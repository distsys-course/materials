use std::collections::HashSet;
use std::time::Duration;

use rand::prelude::*;
use rand_pcg::Pcg64;

use dslab_mp::logger::LogEntry;
use dslab_mp::mc::events::EventOrderingMode;
use dslab_mp::mc::model_checker::ModelChecker;
use dslab_mp::mc::predicates::{collects, goals, invariants, prunes};
use dslab_mp::mc::state::McState;
use dslab_mp::mc::strategies::bfs::Bfs;
use dslab_mp::mc::strategy::{InvariantFn, McStats, StrategyConfig};
use dslab_mp::mc::system::McSystem;
use dslab_mp::message::Message;
use dslab_mp::system::System;
use dslab_mp::test::TestResult;

use crate::common::*;

pub fn test_mc_empty_system(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let procs = sys.process_names();
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let mut mc = ModelChecker::new(&sys);

    let key = random_string(8, &mut rand).to_uppercase();
    let replicas = key_replicas(&key, &sys);
    let non_replicas = key_non_replicas(&key, &sys);
    println!("Key {} replicas: {:?}", key, replicas);
    println!("Key {} non-replicas: {:?}", key, non_replicas);

    // stage 1: get key from the first node
    let stage1_strategy = mc_query_strategy(&procs[0], McQuery::Get(key.clone(), vec![]));
    let stage1_msg = Message::json(
        "GET",
        &GetReqMessage {
            key: &key,
            quorum: 2,
        },
    );
    let stage1_states = run_mc(
        &mut mc,
        stage1_strategy,
        &procs[0],
        stage1_msg,
        McNetworkChange::None,
        None,
    )?
    .collected_states;
    println!("stage 1: {}", stage1_states.len());
    if stage1_states.is_empty() {
        return Err("stage 1 - GET response is not received".to_owned());
    }
    Ok(true)
}

pub fn test_mc_basic(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let mut mc = ModelChecker::new(&sys);

    let key = random_string(8, &mut rand).to_uppercase();
    let replicas = key_replicas(&key, &sys);
    let non_replicas = key_non_replicas(&key, &sys);
    println!("Key {} replicas: {:?}", key, replicas);
    println!("Key {} non-replicas: {:?}", key, non_replicas);

    // stage 1: put key to the first replica
    let value = random_string(8, &mut rand);
    let stage1_strategy =
        mc_query_strategy(&replicas[0], McQuery::Put(key.clone(), vec![value.clone()]));
    let stage1_strategy = stage1_strategy.prune(prunes::any_prune(vec![
        prunes::event_happened_n_times_current_run(LogEntry::is_mc_timer_fired, 2),
        prunes::event_happened_n_times_current_run(LogEntry::is_mc_message_received, 24),
        prunes::proc_permutations(&replicas),
    ]));
    let stage1_msg = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value,
            quorum: 2,
            context: None,
        },
    );
    let stage1_states = run_mc(
        &mut mc,
        stage1_strategy,
        &replicas[0],
        stage1_msg,
        McNetworkChange::None,
        None,
    )?
    .collected_states;
    println!("stage 1: {}", stage1_states.len());
    if stage1_states.is_empty() {
        return Err("stage 1 - PUT response is not received".to_owned());
    }

    // stage 2: get key from the last replica
    let stage2_strategy = mc_query_strategy(&replicas[2], McQuery::Get(key.clone(), vec![value]));
    let stage2_strategy = stage2_strategy.prune(prunes::any_prune(vec![
        prunes::event_happened_n_times_current_run(LogEntry::is_mc_timer_fired, 4),
        prunes::event_happened_n_times_current_run(LogEntry::is_mc_message_received, 24),
        // symmetry-breaking constraint: log starts with replica 2 (because it received the query)
        // and then the replica 0 should be earlier in the log than replica 1.
        prunes::proc_permutations(&[
            replicas[2].clone(),
            replicas[0].clone(),
            replicas[1].clone(),
        ]),
    ]));
    let stage2_msg = Message::json(
        "GET",
        &GetReqMessage {
            key: &key,
            quorum: 2,
        },
    );
    let stage2_states = run_mc(
        &mut mc,
        stage2_strategy,
        &replicas[2],
        stage2_msg,
        McNetworkChange::None,
        Some(stage1_states),
    )?
    .collected_states;
    println!("stage 2: {}", stage2_states.len());
    if stage2_states.is_empty() {
        return Err("stage 2 - GET response is not received".to_owned());
    }
    Ok(true)
}

pub fn test_mc_concurrent_writes(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let key = random_string(8, &mut rand).to_uppercase();
    let replicas = key_replicas(&key, &sys);
    let non_replicas = key_non_replicas(&key, &sys);
    println!("Key {} replicas: {:?}", key, replicas);
    println!("Key {} non-replicas: {:?}", key, non_replicas);

    let mut mc = ModelChecker::new(&sys);

    // put (key, value) to the first replica
    // and then put (key, value2) to the second replica
    let value = random_string(8, &mut rand);
    let value2 = random_string(8, &mut rand);

    let strategy_config =
        mc_query_strategy(&replicas[0], McQuery::Put(key.clone(), vec![value.clone()]));
    let msg1 = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value,
            quorum: 1,
            context: None,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[0],
        msg1,
        McNetworkChange::Isolation,
        None,
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("put({key}, {value}) response is not received"));
    }
    println!("put({key}, {value}): {} states collected", states.len());

    let strategy_config = mc_query_strategy(
        &replicas[1],
        McQuery::Put(key.clone(), vec![value2.clone()]),
    );
    let msg2 = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value2,
            quorum: 1,
            context: None,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[1],
        msg2,
        McNetworkChange::None,
        Some(states),
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("put({key}, {value2}) response is not received"));
    }
    println!("put({key}, {value2}): {} states collected", states.len());

    // now reset the network state and ask the third replica about the key's value
    // we expect both values in the response
    let strategy_config = mc_query_strategy(
        &replicas[2],
        McQuery::Get(key.to_string(), vec![value.to_string(), value2.to_string()]),
    );
    let msg = Message::json(
        "GET",
        &GetReqMessage {
            key: &key,
            quorum: 3,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[2],
        msg,
        McNetworkChange::Reset,
        Some(states),
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("get({key}) response is not received"));
    }
    println!("get({key}): {} states collected", states.len());
    Ok(true)
}

pub fn test_mc_sloppy_quorum_hinted_handoff(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let mut mc = ModelChecker::new(&sys);

    let key = random_string(8, &mut rand).to_uppercase();
    let replicas = key_replicas(&key, &sys);
    let non_replicas = key_non_replicas(&key, &sys);
    println!("Key {} replicas: {:?}", key, replicas);
    println!("Key {} non-replicas: {:?}", key, non_replicas);

    // stage 1: put key from the first replica (network partition still exists)
    let value = random_string(8, &mut rand);
    let stage1_strategy =
        mc_query_strategy(&replicas[0], McQuery::Put(key.clone(), vec![value.clone()]));
    let stage1_msg = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value,
            quorum: 2,
            context: None,
        },
    );
    let stage1_states = run_mc(
        &mut mc,
        stage1_strategy,
        &replicas[0],
        stage1_msg,
        McNetworkChange::Partition([
            vec![
                replicas[0].clone(),
                non_replicas[0].clone(),
                non_replicas[1].clone(),
                non_replicas[2].clone(),
            ],
            vec![replicas[1].clone(), replicas[2].clone()],
        ]),
        None,
    )?
    .collected_states;
    println!("stage 1: {}", stage1_states.len());
    if stage1_states.is_empty() {
        return Err("stage 1 - PUT response is not received".to_owned());
    }

    // stage 2: recover network and let data propagate to all replicas
    let stage2_states = mc_stabilize(&mut sys, stage1_states)?.collected_states;
    println!("stage 2: {}", stage2_states.len());
    if stage2_states.is_empty() {
        return Err(
            "stage 2 - no states found during the exploration phase with recovered network"
                .to_owned(),
        );
    }

    // stage 3: get key from the last replica (again during the network partition)
    let stage3_strategy = mc_query_strategy(&replicas[2], McQuery::Get(key.clone(), vec![value]));
    let stage3_msg = Message::json(
        "GET",
        &GetReqMessage {
            key: &key,
            quorum: 2,
        },
    );
    let stage3_states = run_mc(
        &mut mc,
        stage3_strategy,
        &replicas[2],
        stage3_msg,
        McNetworkChange::Partition([
            vec![
                replicas[0].clone(),
                non_replicas[0].clone(),
                non_replicas[1].clone(),
                non_replicas[2].clone(),
            ],
            vec![replicas[1].clone(), replicas[2].clone()],
        ]),
        Some(stage2_states),
    )?
    .collected_states;
    println!("stage 3: {}", stage3_states.len());
    if stage3_states.is_empty() {
        return Err("stage 3 - GET response is not received".to_owned());
    }
    Ok(true)
}

pub fn test_mc_concurrent_cart(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let key = format!("CART_{}", random_string(8, &mut rand).to_uppercase());
    let replicas = key_replicas(&key, &sys);
    let non_replicas = key_non_replicas(&key, &sys);
    println!("Key {} replicas: {:?}", key, replicas);
    println!("Key {} non-replicas: {:?}", key, non_replicas);

    // put key to the first replica
    let value = "a,b,c".to_string();
    let value2 = "b,c,d".to_string();

    let mut mc = ModelChecker::new(&sys);

    let strategy_config =
        mc_query_strategy(&replicas[0], McQuery::Put(key.clone(), vec![value.clone()]));
    let msg1 = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value,
            quorum: 1,
            context: None,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[0],
        msg1,
        McNetworkChange::Isolation,
        None,
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("put({key}, \"{value}\") response is not received"));
    }
    println!("put({key}, \"{value}\"): {} states collected", states.len());

    let strategy_config = mc_query_strategy(
        &replicas[1],
        McQuery::Put(key.clone(), vec![value2.clone()]),
    );
    let msg2 = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value2,
            quorum: 1,
            context: None,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[1],
        msg2,
        McNetworkChange::None,
        Some(states),
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("put({key}, \"{value2}\") response is not received"));
    }
    println!(
        "put({key}, \"{value2}\"): {} states collected",
        states.len()
    );

    // Now reset the network state and ask all replicas to agree about value for key
    // We expect the combination of "a,b,c" and "b,c,d"
    let strategy_config = mc_query_strategy(
        &replicas[2],
        McQuery::Get(key.to_string(), vec!["a,b,c,d".to_string()]),
    );
    let msg3 = Message::json(
        "GET",
        &GetReqMessage {
            key: &key,
            quorum: 3,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[2],
        msg3,
        McNetworkChange::Reset,
        Some(states),
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("get({key}) has no positive outcomes"));
    }
    println!("get({key}): {} states collected", states.len());
    Ok(true)
}

pub fn test_mc_concurrent_xcart(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let mut rand = Pcg64::seed_from_u64(config.seed);

    let key = format!("xcart-{}", random_string(8, &mut rand)).to_uppercase();
    let replicas = key_replicas(&key, &sys);
    let mut mc = ModelChecker::new(&sys);

    let value1 = "a,b".to_string();
    let value2 = "a,b,c".to_string();
    let value3 = "d".to_string();
    let value4 = "c,d".to_string();

    let strategy_config = mc_query_strategy(
        &replicas[2],
        McQuery::Put(key.clone(), vec![value1.clone()]),
    );
    let msg1 = Message::json(
        "PUT",
        &PutReqMessage {
            key: &key,
            value: &value1,
            quorum: 3,
            context: None,
        },
    );
    let states = run_mc(
        &mut mc,
        strategy_config,
        &replicas[2],
        msg1,
        McNetworkChange::None,
        None,
    )?
    .collected_states;
    if states.is_empty() {
        return Err(format!("put({key}, \"{value1}\") response is not received"));
    }
    println!("get({key}): {} states collected", states.len());

    let states = mc_stabilize(&mut sys, states)?.collected_states;
    println!("after stabilization: {} states collected", states.len());

    for state in &states {
        let msg = &state.node_states[&replicas[2]].proc_states[&replicas[2]].local_outbox[0];
        let data: PutRespMessage =
            serde_json::from_str(&msg.data).map_err(|err| err.to_string())?;
        let ctx = data.context.to_string();

        let msg1 = Message::json(
            "PUT",
            &PutReqMessage {
                key: &key,
                value: &value2,
                quorum: 1,
                context: Some(ctx.clone()),
            },
        );
        let strategy_config = mc_query_strategy(
            &replicas[0],
            McQuery::Put(key.clone(), vec![value2.clone()]),
        );
        mc = ModelChecker::new(&sys);
        let cur_states: HashSet<McState> = run_mc(
            &mut mc,
            strategy_config,
            &replicas[0],
            msg1,
            McNetworkChange::Isolation,
            Some(HashSet::from_iter(vec![state.clone()])),
        )?
        .collected_states;
        if states.is_empty() {
            return Err(format!("put({key}, \"{value2}\") response is not received"));
        }

        let msg2 = Message::json(
            "PUT",
            &PutReqMessage {
                key: &key,
                value: &value3,
                quorum: 1,
                context: Some(ctx),
            },
        );
        let strategy_config = mc_query_strategy(
            &replicas[1],
            McQuery::Put(key.clone(), vec![value3.clone()]),
        );
        let cur_states = run_mc(
            &mut mc,
            strategy_config,
            &replicas[1],
            msg2,
            McNetworkChange::Isolation,
            Some(cur_states),
        )?
        .collected_states;
        if states.is_empty() {
            return Err(format!("put({key}, \"{value3}\") response is not received"));
        }

        let msg3 = Message::json(
            "GET",
            &GetReqMessage {
                key: &key,
                quorum: 3,
            },
        );
        let strategy_config = mc_query_strategy(
            &replicas[2],
            McQuery::Get(key.clone(), vec![value4.clone()]),
        );
        run_mc(
            &mut mc,
            strategy_config,
            &replicas[2],
            msg3,
            McNetworkChange::Reset,
            Some(cur_states),
        )?;
        if states.is_empty() {
            return Err(format!("get({key}) response is not received"));
        }
    }
    Ok(true)
}

// UTILS ---------------------------------------------------------------------------------------------------------------

enum McQuery {
    Get(String, Vec<String>),
    Put(String, Vec<String>),
}

fn mc_query_strategy(proc: &str, query_data: McQuery) -> StrategyConfig {
    let proc_name = proc.to_string();

    let invariant = match query_data {
        McQuery::Get(key, expected) => mc_get_invariant(proc, key, expected),
        McQuery::Put(key, value) => mc_put_invariant(proc, key, value),
    };

    StrategyConfig::default()
        .prune(prunes::any_prune(vec![
            prunes::event_happened_n_times_current_run(LogEntry::is_mc_timer_fired, 5_usize),
            prunes::event_happened_n_times_current_run(LogEntry::is_mc_message_received, 10_usize),
        ]))
        .goal(goals::event_happened_n_times_current_run(
            LogEntry::is_mc_local_message_sent,
            1,
        ))
        .invariant(invariants::all_invariants(vec![
            invariant,
            invariants::time_limit(Duration::from_secs(120)),
        ]))
        .collect(collects::event_happened_n_times_current_run(
            move |log_entry| match log_entry {
                LogEntry::McLocalMessageSent { proc, .. } => proc == &proc_name,
                _ => false,
            },
            1,
        ))
}

fn mc_get_invariant<S>(proc: S, key: String, expected: Vec<String>) -> InvariantFn
where
    S: Into<String>,
{
    let proc_name = proc.into();
    Box::new(move |state: &McState| -> Result<(), String> {
        for entry in state.current_run_trace().iter() {
            if let LogEntry::McLocalMessageSent { msg, proc } = entry {
                if &proc_name != proc {
                    return Err("local message received on wrong process".to_string());
                }
                if msg.tip != "GET_RESP" {
                    return Err(format!("wrong type {}", msg.tip));
                }
                let data: GetRespMessage =
                    serde_json::from_str(&msg.data).map_err(|err| err.to_string())?;
                if data.key != key {
                    return Err(format!("wrong key {}", data.key));
                }
                if sorted_cart(&data.values)
                    != sorted_cart(&expected.iter().map(|x| x.as_str()).collect())
                {
                    return Err(format!("wrong values {:?}", sorted_cart(&data.values)));
                }
            }
        }
        Ok(())
    })
}

fn mc_put_invariant<S>(proc: S, key: String, values: Vec<String>) -> InvariantFn
where
    S: Into<String>,
{
    let proc_name = proc.into();
    Box::new(move |state: &McState| -> Result<(), String> {
        for entry in state.current_run_trace().iter() {
            if let LogEntry::McLocalMessageSent { msg, proc } = entry {
                if &proc_name != proc {
                    return Err("local message received on wrong process".to_string());
                }
                if msg.tip != "PUT_RESP" {
                    return Err(format!("wrong type {}", msg.tip));
                }
                let data: PutRespMessage =
                    serde_json::from_str(&msg.data).map_err(|err| err.to_string())?;
                if data.key != key {
                    return Err(format!("wrong key {}", data.key));
                }
                if sorted_cart(&data.values)
                    != sorted_cart(&values.iter().map(|x| x.as_str()).collect())
                {
                    return Err(format!("wrong values {:?}", sorted_cart(&data.values)));
                }
            }
        }
        Ok(())
    })
}

fn sorted_cart(cart: &Vec<&str>) -> Vec<String> {
    let mut res = vec![];
    for items in cart {
        let mut items = items
            .split(',')
            .map(|s| s.to_owned())
            .collect::<Vec<String>>();
        items.sort();
        res.push(items.join(","));
    }
    res.sort();
    res
}

enum McNetworkChange {
    None,
    Reset,
    Partition([Vec<String>; 2]),
    Isolation,
}

fn run_mc<S>(
    mc: &mut ModelChecker,
    strategy_config: StrategyConfig,
    proc: S,
    msg: Message,
    network_change: McNetworkChange,
    states: Option<HashSet<McState>>,
) -> Result<McStats, String>
where
    S: Into<String>,
{
    let proc = proc.into();

    let callback = |sys: &mut McSystem| {
        match &network_change {
            McNetworkChange::Partition([part1, part2]) => sys.network().partition(part1, part2),
            McNetworkChange::Reset => sys.network().reset(),
            McNetworkChange::Isolation => {
                for node in sys.nodes() {
                    sys.network().disconnect_node(&node)
                }
            }
            McNetworkChange::None => {}
        }
        sys.set_event_ordering_mode(EventOrderingMode::MessagesFirst);
        sys.send_local_message(proc.clone(), proc.clone(), msg.clone());
    };

    let res = if let Some(states) = states {
        mc.run_from_states_with_change::<Bfs>(strategy_config, states, callback)
    } else {
        mc.run_with_change::<Bfs>(strategy_config, callback)
    };
    match res {
        Err(e) => {
            e.print_trace();
            Err(e.message())
        }
        Ok(stats) => Ok(stats),
    }
}

fn mc_stabilize(sys: &mut System, states: HashSet<McState>) -> Result<McStats, String> {
    let strategy_config = StrategyConfig::default()
        .prune(prunes::any_prune(vec![
            prunes::event_happened_n_times_current_run(LogEntry::is_mc_timer_fired, 6),
            prunes::event_happened_n_times_current_run(LogEntry::is_mc_message_received, 24),
        ]))
        .goal(goals::any_goal(vec![
            goals::depth_reached(30),
            goals::no_events(),
        ]))
        .collect(collects::any_collect(vec![
            collects::no_events(),
            collects::event_happened_n_times_current_run(LogEntry::is_mc_timer_fired, 6),
            collects::event_happened_n_times_current_run(LogEntry::is_mc_message_received, 24),
        ]));
    let mut mc = ModelChecker::new(sys);
    let res = mc.run_from_states_with_change::<Bfs>(strategy_config, states, |sys| {
        sys.network().reset();
        sys.set_event_ordering_mode(EventOrderingMode::MessagesFirst);
    });
    match res {
        Err(e) => {
            e.print_trace();
            Err(e.message())
        }
        Ok(stats) => Ok(stats),
    }
}
