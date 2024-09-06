use std::collections::HashSet;

use anysystem::logger::LogEntry;
use anysystem::mc::{
    predicates::{collects, goals, invariants, prunes},
    strategies::Bfs,
    ModelChecker, StrategyConfig,
};
use anysystem::test::TestResult;
use anysystem::Message;

use crate::common::{build_system, TestConfig};

pub fn test_mc_reliable_network(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let data = r#"{"value": 0}"#.to_string();
    let messages_expected = HashSet::<String>::from_iter([data.clone()]);

    let strategy_config = StrategyConfig::default()
        .prune(prunes::sent_messages_limit(4))
        .goal(goals::got_n_local_messages("client-node", "client", 1))
        .invariant(invariants::all_invariants(vec![
            invariants::received_messages("client-node", "client", messages_expected),
            invariants::state_depth(20),
        ]));

    let mut mc = ModelChecker::new(&sys);
    let res = mc.run_with_change::<Bfs>(strategy_config, |system| {
        system.send_local_message("client-node", "client", Message::new("PING", &data));
    });

    if let Err(e) = res {
        e.print_trace();
        Err(e.message())
    } else {
        Ok(true)
    }
}

pub fn test_mc_unreliable_network(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let data = r#"{"value": 0}"#.to_string();
    let messages_expected = HashSet::<String>::from_iter([data.clone()]);
    sys.network().set_drop_rate(0.5);
    let strategy_config = StrategyConfig::default()
        .prune(prunes::state_depth(7))
        .goal(goals::got_n_local_messages("client-node", "client", 1))
        .invariant(invariants::received_messages(
            "client-node",
            "client",
            messages_expected,
        ));
    let mut mc = ModelChecker::new(&sys);

    let res = mc.run_with_change::<Bfs>(strategy_config, |system| {
        system.send_local_message("client-node", "client", Message::new("PING", &data));
    });

    if let Err(e) = res {
        e.print_trace();
        Err(e.message())
    } else {
        Ok(true)
    }
}

pub fn test_mc_limited_message_drops(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    sys.network().set_drop_rate(0.5);
    let data = r#"{"value": 0}"#.to_string();
    let messages_expected = HashSet::<String>::from_iter([data.clone()]);
    let num_drops_allowed = 3;
    let strategy_config = StrategyConfig::default()
        .prune(prunes::any_prune(vec![
            prunes::events_limit(LogEntry::is_mc_message_dropped, num_drops_allowed),
            prunes::events_limit(LogEntry::is_mc_message_sent, 2 + num_drops_allowed),
        ]))
        .goal(goals::got_n_local_messages("client-node", "client", 1))
        .invariant(invariants::received_messages(
            "client-node",
            "client",
            messages_expected,
        ));
    let mut mc = ModelChecker::new(&sys);

    let res = mc.run_with_change::<Bfs>(strategy_config, |system| {
        system.send_local_message("client-node", "client", Message::new("PING", &data));
    });

    if let Err(e) = res {
        e.print_trace();
        Err(e.message())
    } else {
        Ok(true)
    }
}

pub fn test_mc_consecutive_messages(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let data = r#"{"value": 0}"#.to_string();
    let data2 = r#"{"value": 1}"#.to_string();

    let messages_data = [data, data2];
    let mut messages_expected = HashSet::new();
    let mut collected_states = HashSet::new();

    for (message_data, i) in messages_data.iter().zip(1u64..) {
        messages_expected.insert(message_data.clone());
        let strategy_config = StrategyConfig::default()
            .prune(prunes::sent_messages_limit(2 * i))
            .goal(goals::all_goals(vec![
                goals::no_events(),
                goals::got_n_local_messages("client-node", "client", i as usize),
            ]))
            .invariant(invariants::all_invariants(vec![
                invariants::received_messages("client-node", "client", messages_expected.clone()),
                invariants::state_depth(20 * i),
            ]))
            .collect(collects::got_n_local_messages(
                "client-node",
                "client",
                i as usize,
            ));
        let mut mc = ModelChecker::new(&sys);

        let res = if i == 1 {
            mc.run_with_change::<Bfs>(strategy_config, |system| {
                system.send_local_message(
                    "client-node",
                    "client",
                    Message::new("PING", message_data),
                );
            })
        } else {
            mc.run_from_states_with_change::<Bfs>(strategy_config, collected_states, |system| {
                system.send_local_message(
                    "client-node",
                    "client",
                    Message::new("PING", message_data),
                );
            })
        };
        match res {
            Err(e) => {
                e.print_trace();
                return Err(e.message());
            }
            Ok(stats) => {
                // uncomment to see how many intermediate states were collected:
                println!("{}", stats.collected_states.len());
                collected_states = stats.collected_states;
            }
        }
    }
    Ok(true)
}
