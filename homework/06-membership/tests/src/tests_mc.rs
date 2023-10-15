use std::collections::HashSet;
use std::time::Duration;

use rand::prelude::*;
use rand_pcg::Pcg64;
use sugars::boxed;

use dslab_mp::logger::{LogEntry, LogEntry::McMessageReceived};
use dslab_mp::mc::events::EventOrderingMode;
use dslab_mp::mc::model_checker::ModelChecker;
use dslab_mp::mc::predicates::{collects, goals, invariants, prunes};
use dslab_mp::mc::state::McState;
use dslab_mp::mc::strategies::bfs::Bfs;
use dslab_mp::mc::strategy::{CollectFn, InvariantFn, StrategyConfig};
use dslab_mp::message::Message;
use dslab_mp::system::System;
use dslab_mp::test::TestResult;

use crate::common::*;

pub fn test_mc_group(config: &TestConfig) -> TestResult {
    let mut rand = Pcg64::seed_from_u64(config.seed);
    let mut sys = build_system(config);
    let group = sys.process_names();
    let seed = group.choose(&mut rand).unwrap();

    let collected_states = mc_explore_after_joins(&mut sys, seed.to_string())?;
    if collected_states.is_empty() {
        return Err("no states collected during explore stage".to_string());
    }
    mc_check_members(&mut sys, collected_states)
}

fn mc_explore_after_joins(sys: &mut System, seed_proc: String) -> Result<HashSet<McState>, String> {
    let procs = sys.process_names();
    let mut mc = ModelChecker::new(sys);

    let strategy_config = StrategyConfig::default()
        // Explore only states with up to 2 timer firings per process
        // (we expect each process to communicate with others at most 3 times:
        // 1 time on a local message and 2 times on a timer).
        .prune(prunes::events_limit_per_proc(
            |entry: &LogEntry, proc_name: &String| match entry {
                LogEntry::McTimerFired { proc, .. } => proc_name == proc,
                _ => false,
            },
            procs.clone(),
            2,
        ))
        // Stop when no events left or reached depth 20 (steps of simulation).
        .goal(goals::any_goal(vec![
            goals::no_events(),
            goals::depth_reached(20),
        ]))
        // Time limit is set to 2 minutes, which should be more than enough.
        .invariant(invariants::time_limit(Duration::from_secs(120)))
        // Collect states in which the group should be stabilized, namely:
        // either no events left, or every process received at least 3 messages.
        //
        // Considering a system with 3 processes and a stable network, we can show this is enough:
        // * seed process (A) should get information from both other processes (B & C)
        // * because C joins later than B, it will know the full group as well
        // * B is able to get information about the full group either from A or C, depending on implementation
        //
        // Technically, there can be execution A <-> B (x3), A <-> C (x3) where B's information becomes outdated,
        // but we consider solution wrong if it allows such execution.
        .collect(collects::any_collect(vec![
            collects::no_events(),
            collects::all_collects(
                procs
                    .clone()
                    .into_iter()
                    .map(|proc_name| {
                        collects::event_happened_n_times_current_run(
                            move |log_entry| match log_entry {
                                McMessageReceived { dst: proc, .. } => proc == &proc_name,
                                _ => false,
                            },
                            3,
                        )
                    })
                    .collect::<Vec<CollectFn>>(),
            ),
        ]));

    let res = mc.run_with_change::<Bfs>(strategy_config, |sys| {
        // Use event ordering mode which prioritizes messages over timers
        // (this emulates perfect network where timeouts do not occur).
        sys.set_event_ordering_mode(EventOrderingMode::MessagesFirst);
        for proc in &procs {
            sys.send_local_message(
                proc.clone(),
                proc.clone(),
                Message::json("JOIN", &JoinMessage { seed: &seed_proc }),
            );
        }
    });
    match res {
        Err(e) => {
            e.print_trace();
            Err(e.message())
        }
        Ok(stats) => {
            // println!("collected {} states", stats.collected_states.len());
            Ok(stats.collected_states)
        }
    }
}

fn mc_check_members(sys: &mut System, collected: HashSet<McState>) -> TestResult {
    let procs = sys.process_names();
    let mut mc = ModelChecker::new(sys);
    let strategy_config = StrategyConfig::default()
        .invariant(mc_invariant_check_stabilized(procs.clone()))
        .goal(goals::always_ok());

    let res = mc.run_from_states_with_change::<Bfs>(strategy_config, collected, |sys| {
        for node in procs.iter() {
            sys.send_local_message(
                node,
                node,
                Message::json("GET_MEMBERS", &GetMembersMessage {}),
            );
        }
    });
    if let Err(e) = res {
        e.print_trace();
        Err(e.message())
    } else {
        Ok(true)
    }
}

fn mc_invariant_check_stabilized(group: Vec<String>) -> InvariantFn {
    boxed!(move |state| {
        let group = group.clone().into_iter().collect::<HashSet<String>>();
        for node in state.node_states.keys() {
            if let Some(msg) = state.node_states[node].proc_states[node]
                .local_outbox
                .first()
            {
                if msg.tip != "MEMBERS" {
                    return Err("wrong message type".to_owned());
                }
                let data: MembersMessage = serde_json::from_str(&msg.data).unwrap();
                let members = HashSet::from_iter(data.members.into_iter());
                if !members.eq(&group) {
                    return Err(format!(
                        "expected a stabilized group {:?} but got {:?}",
                        group, members
                    ));
                }
            }
        }
        Ok(())
    })
}
