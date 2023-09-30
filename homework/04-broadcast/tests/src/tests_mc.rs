use std::collections::HashSet;
use std::time::Duration;

use serde_json::Value;
use sugars::boxed;

use dslab_mp::logger::LogEntry;
use dslab_mp::message::Message;
use dslab_mp::test::TestResult;

use dslab_mp::mc::model_checker::ModelChecker;
use dslab_mp::mc::predicates::{collects, goals, invariants, prunes};
use dslab_mp::mc::state::McState;
use dslab_mp::mc::strategies::bfs::Bfs;
use dslab_mp::mc::strategy::{GoalFn, InvariantFn, PruneFn, StrategyConfig};

use crate::common::{build_system, BroadcastMessage, TestConfig};

pub fn test_mc_normal_delivery(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let proc_names = sys.process_names();
    let text = "0:Hello";
    sys.send_local_message(
        proc_names[0].as_str(),
        Message::json("SEND", &BroadcastMessage { text }),
    );
    let goal = goals::all_goals(
        proc_names
            .iter()
            .map(|name| goals::got_n_local_messages(name, name, 1))
            .collect::<Vec<GoalFn>>(),
    );
    let strategy_config = StrategyConfig::default()
        .goal(goal)
        .prune(prunes::any_prune(vec![
            prunes::state_depth(10),
            mc_prune_proc_permutations(&proc_names[1..]),
            // Prune states with more than 2 messages received from any process
            mc_prune_msg_per_proc_limit(&proc_names, 2),
        ]))
        .invariant(invariants::all_invariants(vec![
            mc_invariant(proc_names.clone(), text.to_string()),
            invariants::time_limit(Duration::from_secs(100)),
        ]));
    let mut mc = ModelChecker::new(&sys);
    let res = mc.run::<Bfs>(strategy_config);
    if let Err(err) = res {
        err.print_trace();
        Err(err.message())
    } else {
        Ok(true)
    }
}

pub fn test_mc_sender_crash(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let proc_names = sys.process_names();
    let text = "0:Hello";
    sys.send_local_message(
        proc_names[0].as_str(),
        Message::json("SEND", &BroadcastMessage { text }),
    );
    let goal = goals::all_goals(
        proc_names
            .iter()
            .map(|name| goals::got_n_local_messages(name, name, 1))
            .collect::<Vec<GoalFn>>(),
    );

    let strategy_config = StrategyConfig::default()
        .prune(prunes::any_prune(vec![
            prunes::state_depth(4),
            mc_prune_proc_permutations(&proc_names[1..]),
        ]))
        .goal(goal)
        .invariant(invariants::all_invariants(vec![
            mc_invariant(proc_names.clone(), text.to_string()),
            invariants::time_limit(Duration::from_secs(100)),
        ]))
        .collect(collects::any_collect(
            proc_names[1..]
                .iter()
                .map(|proc| collects::got_n_local_messages(proc, proc, 1))
                .collect(),
        ));

    let mut mc = ModelChecker::new(&sys);
    let res = mc.run::<Bfs>(strategy_config);
    let intermediate_states = res
        .map_err(|err| {
            err.print_trace();
            err.message()
        })?
        .collected_states;
    if intermediate_states.is_empty() {
        return Err("no states collected after first stage".to_string());
    }

    // Crash first node in the list
    let left_proc_names = proc_names[1..].to_vec();
    let goal = goals::all_goals(
        left_proc_names
            .iter()
            .map(|name| goals::got_n_local_messages(name, name, 1))
            .collect::<Vec<GoalFn>>(),
    );
    let strategy_config = StrategyConfig::default()
        .goal(goal)
        .invariant(invariants::all_invariants(vec![
            mc_invariant(left_proc_names, text.to_string()),
            invariants::time_limit(Duration::from_secs(100)),
        ]))
        .prune(prunes::any_prune(vec![
            prunes::state_depth(6),
            mc_prune_proc_permutations(&proc_names[1..]),
            // Prune states with more than 4 messages received from any process
            mc_prune_msg_per_proc_limit(&proc_names, 4),
        ]));
    let res = mc.run_from_states_with_change::<Bfs>(strategy_config, intermediate_states, |sys| {
        sys.crash_node(proc_names[0].clone());
    });
    if let Err(err) = res {
        err.print_trace();
        Err(err.message())
    } else {
        Ok(true)
    }
}

fn mc_prune_proc_permutations(equivalent_procs: &[String]) -> PruneFn {
    let equivalent_procs = equivalent_procs.to_vec();
    boxed!(move |state| {
        let proc_names = HashSet::<String>::from_iter(equivalent_procs.clone().into_iter());
        let mut used_proc_names = HashSet::<String>::new();
        let mut waiting_for_proc = 0;
        for entry in &state.trace {
            match entry {
                LogEntry::McMessageReceived { src: proc, .. }
                | LogEntry::McTimerFired { proc, .. } => {
                    if used_proc_names.contains(proc) || !proc_names.contains(proc) {
                        continue;
                    }
                    if equivalent_procs[waiting_for_proc] != *proc {
                        return Some(
                            "state is the same as another state with renumerated processes"
                                .to_owned(),
                        );
                    }
                    used_proc_names.insert(proc.clone());
                    waiting_for_proc += 1;
                }
                _ => {}
            }
        }
        None
    })
}

fn mc_prune_msg_per_proc_limit(proc_names: &[String], limit: usize) -> PruneFn {
    prunes::events_limit_per_proc(
        |entry: &LogEntry, proc: &String| match entry {
            LogEntry::McMessageReceived { src, .. } => src == proc,
            _ => false,
        },
        proc_names.to_owned(),
        limit,
    )
}

fn mc_invariant(proc_names: Vec<String>, sent_message: String) -> InvariantFn {
    boxed!(move |state: &McState| {
        for name in &proc_names {
            let outbox = &state.node_states[name].proc_states[name].local_outbox;
            let mut message_data = HashSet::new();
            for message in outbox {
                let data: Value = serde_json::from_str(&message.data).unwrap();
                let message = data["text"].as_str().unwrap().to_string();

                if message_data.contains(&message) {
                    return Err("No duplication violated".to_owned());
                }
                message_data.insert(message.clone());
                if message != sent_message {
                    return Err("No creation violated".to_owned());
                }
            }
        }
        Ok(())
    })
}
