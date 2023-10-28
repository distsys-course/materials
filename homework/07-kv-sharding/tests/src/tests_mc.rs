use std::collections::{HashMap, HashSet};

use rand::prelude::SliceRandom;
use rand::SeedableRng;
use rand_pcg::Pcg64;
use sugars::boxed;

use dslab_mp::logger::LogEntry;
use dslab_mp::mc::model_checker::ModelChecker;
use dslab_mp::mc::predicates::{collects, goals, invariants};
use dslab_mp::mc::state::McState;
use dslab_mp::mc::strategies::bfs::Bfs;
use dslab_mp::mc::strategy::{InvariantFn, StrategyConfig};
use dslab_mp::message::Message;
use dslab_mp::test::TestResult;

use crate::common::*;

pub fn test_mc_normal(config: &TestConfig) -> TestResult {
    let sys = build_system(config, false);
    let mut mc = ModelChecker::new(&sys);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let key = random_string(8, &mut rand).to_uppercase();
    let value = random_string(8, &mut rand);
    let max_steps = 10;

    let mut proc = random_proc(&sys, &mut rand);
    let achieved_states = check_mc_get(&mut mc, &proc, &key, None, max_steps, None)?;
    proc = random_proc(&sys, &mut rand);
    let achieved_states = check_mc_put(
        &mut mc,
        &proc,
        &key,
        &value,
        max_steps,
        Some(achieved_states),
    )?;
    proc = random_proc(&sys, &mut rand);
    let achieved_states = check_mc_get(
        &mut mc,
        &proc,
        &key,
        Some(&value),
        max_steps,
        Some(achieved_states),
    )?;
    proc = random_proc(&sys, &mut rand);
    let achieved_states = check_mc_delete(
        &mut mc,
        &proc,
        &key,
        Some(&value),
        max_steps,
        Some(achieved_states),
    )?;
    proc = random_proc(&sys, &mut rand);
    let achieved_states =
        check_mc_get(&mut mc, &proc, &key, None, max_steps, Some(achieved_states))?;
    proc = random_proc(&sys, &mut rand);
    check_mc_delete(&mut mc, &proc, &key, None, max_steps, Some(achieved_states))?;
    Ok(true)
}

pub fn test_mc_node_removed(config: &TestConfig) -> TestResult {
    let sys = build_system(config, false);
    let mut mc = ModelChecker::new(&sys);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    // insert random key-value pairs
    let keys_count = 40;
    let mut achieved_states = None;
    let mut kv = HashMap::new();
    for _ in 0..keys_count {
        let k = random_string(8, &mut rand).to_uppercase();
        let v = random_string(8, &mut rand);
        let proc = random_proc(&sys, &mut rand);
        let res = check_mc_put(&mut mc, &proc, &k, &v, 10, achieved_states)?;
        achieved_states = Some(res);
        kv.insert(k, v);
    }

    // remove a node from the system
    let removed_proc = random_proc(&sys, &mut rand);
    achieved_states = Some(check_mc_node_removed(
        &mut mc,
        sys.process_names(),
        &removed_proc,
        15,
        achieved_states
            .unwrap_or_else(|| panic!("no states found after {} GET queries", keys_count)),
    )?);
    let alive_proc = sys
        .process_names()
        .into_iter()
        .filter(|proc| *proc != removed_proc)
        .collect::<Vec<String>>();

    // check that all data is still in the storage
    for (k, v) in kv {
        let proc = alive_proc.choose(&mut rand).unwrap().clone();
        achieved_states = Some(check_mc_get(
            &mut mc,
            &proc,
            &k,
            Some(&v),
            10,
            achieved_states,
        )?);
    }
    Ok(true)
}

// UTILS ---------------------------------------------------------------------------------------------------------------

fn check_mc_get<S>(
    mc: &mut ModelChecker,
    proc: S,
    key: S,
    expected: Option<S>,
    max_steps: u64,
    start_states: Option<HashSet<McState>>,
) -> Result<HashSet<McState>, String>
where
    S: Into<String> + Clone,
{
    let proc = proc.into();
    let key = key.into();
    let expected = expected.map(|s| s.into());
    let msg = Message::new("GET", &format!(r#"{{"key": "{}"}}"#, key));
    let proc_name = proc.clone();
    let invariant = boxed!(move |state: &McState| {
        for entry in state.current_run_trace().iter() {
            if let LogEntry::McLocalMessageSent {
                msg: message,
                proc: proc_tmp,
            } = entry
            {
                if *proc_tmp != proc {
                    return Err("local message received on wrong process".to_string());
                }
                if message.tip != "GET_RESP" {
                    return Err(format!("wrong type {}", message.tip));
                }
                let data: GetRespMessage =
                    serde_json::from_str(&message.data).map_err(|err| err.to_string())?;
                if data.key != key {
                    return Err(format!("wrong key {}", data.key));
                }
                if data.value.map(|s| s.to_string()) != expected {
                    return Err(format!("wrong value {:?}", data.value));
                }
            }
        }
        Ok(())
    });
    mc_check_query(mc, proc_name, invariant, msg, start_states, max_steps)
}

fn check_mc_put<S>(
    mc: &mut ModelChecker,
    proc: S,
    key: S,
    value: S,
    max_steps: u64,
    start_states: Option<HashSet<McState>>,
) -> Result<HashSet<McState>, String>
where
    S: Into<String>,
{
    let proc = proc.into();
    let key = key.into();
    let value = value.into();
    let proc_name = proc.clone();
    let msg = Message::new(
        "PUT",
        &format!(r#"{{"key": "{}", "value": "{}"}}"#, key, value),
    );
    let invariant = Box::new(move |state: &McState| {
        for entry in state.current_run_trace().iter() {
            if let LogEntry::McLocalMessageSent {
                msg: message,
                proc: proc_tmp,
            } = entry
            {
                if *proc_tmp != proc {
                    return Err("local message received on wrong process".to_string());
                }
                if message.tip != "PUT_RESP" {
                    return Err(format!("wrong type {}", message.tip));
                }
                let data: PutRespMessage =
                    serde_json::from_str(&message.data).map_err(|err| err.to_string())?;
                if data.key != key {
                    return Err(format!("wrong key {}", data.key));
                }
                if data.value != value {
                    return Err(format!("wrong value {:?}", data.value));
                }
            }
        }
        Ok(())
    });
    mc_check_query(mc, proc_name, invariant, msg, start_states, max_steps)
}

fn check_mc_delete<S>(
    mc: &mut ModelChecker,
    proc: S,
    key: S,
    expected: Option<S>,
    max_steps: u64,
    start_states: Option<HashSet<McState>>,
) -> Result<HashSet<McState>, String>
where
    S: Into<String> + Clone,
{
    let proc = proc.into();
    let key = key.into();
    let expected = expected.map(|s| s.into());
    let msg = Message::new("DELETE", &format!(r#"{{"key": "{}"}}"#, key));
    let proc_name = proc.clone();
    let invariant = Box::new(move |state: &McState| {
        for entry in state.current_run_trace().iter() {
            if let LogEntry::McLocalMessageSent {
                msg: message,
                proc: proc_tmp,
            } = entry
            {
                if *proc_tmp != proc {
                    return Err("local message received on wrong process".to_string());
                }
                if message.tip != "DELETE_RESP" {
                    return Err(format!("wrong type {}", message.tip));
                }
                let data: DeleteRespMessage =
                    serde_json::from_str(&message.data).map_err(|err| err.to_string())?;
                if data.key != key {
                    return Err(format!("wrong key {}", data.key));
                }
                if data.value.map(|s| s.to_string()) != expected {
                    return Err(format!("wrong value {:?}", data.value));
                }
            }
        }
        Ok(())
    });
    mc_check_query(mc, proc_name, invariant, msg, start_states, max_steps)
}

fn check_mc_node_removed(
    mc: &mut ModelChecker,
    process_names: Vec<String>,
    removed_proc: &str,
    max_steps: u64,
    start_states: HashSet<McState>,
) -> Result<HashSet<McState>, String> {
    let strategy_config = StrategyConfig::default()
        .invariant(invariants::state_depth_current_run(max_steps))
        .goal(goals::no_events())
        .collect(collects::no_events());

    let res = mc.run_from_states_with_change::<Bfs>(strategy_config, start_states, move |sys| {
        let msg = Message::new("NODE_REMOVED", &format!(r#"{{"id": "{}"}}"#, removed_proc));
        for proc in process_names.clone() {
            sys.send_local_message(proc.clone(), proc, msg.clone());
        }
    });
    match res {
        Ok(stats) => Ok(stats
            .collected_states
            .into_iter()
            .map(|mut state| {
                state.network.disconnect_node(removed_proc);
                state
            })
            .collect::<HashSet<McState>>()),
        Err(err) => {
            err.print_trace();
            Err(err.message())
        }
    }
}

fn mc_check_query<S>(
    mc: &mut ModelChecker,
    proc: S,
    invariant: InvariantFn,
    msg: Message,
    start_states: Option<HashSet<McState>>,
    max_depth: u64,
) -> Result<HashSet<McState>, String>
where
    S: Into<String>,
{
    let proc = proc.into();
    let strategy_config = StrategyConfig::default()
        .goal(goals::all_goals(vec![
            goals::event_happened_n_times_current_run(LogEntry::is_mc_local_message_sent, 1),
            goals::no_events(),
        ]))
        .invariant(invariants::all_invariants(vec![
            invariant,
            invariants::state_depth_current_run(max_depth),
        ]))
        .collect(collects::event_happened_n_times_current_run(
            LogEntry::is_mc_local_message_sent,
            1,
        ));

    let res = if let Some(start_states) = start_states {
        mc.run_from_states_with_change::<Bfs>(strategy_config, start_states, |sys| {
            sys.send_local_message(proc.clone(), proc.clone(), msg.clone());
        })
    } else {
        mc.run_with_change::<Bfs>(strategy_config, |sys| {
            sys.send_local_message(proc.clone(), proc.clone(), msg);
        })
    };
    match res {
        Ok(stats) => Ok(stats.collected_states),
        Err(err) => {
            err.print_trace();
            Err(err.message())
        }
    }
}
