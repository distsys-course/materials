use std::collections::HashSet;
use std::env;
use std::io::Write;

use assertables::assume;
use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;
use sugars::boxed;

use dslab_mp::logger::LogEntry;
use dslab_mp::mc::model_checker::ModelChecker;
use dslab_mp::mc::predicates::{collects, goals, invariants, prunes};
use dslab_mp::mc::strategies::bfs::Bfs;
use dslab_mp::mc::strategy::StrategyConfig;
use dslab_mp::message::Message;
use dslab_mp::system::System;
use dslab_mp::test::{TestResult, TestSuite};
use dslab_mp_python::PyProcessFactory;

// CLI -----------------------------------------------------------------------------------------------------------------

/// Ping-Pong Tests
#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    /// Path to Python file with PingClient and PingServer implementations
    #[clap(long = "impl", short)]
    impl_path: String,

    /// Test to run (optional)
    #[clap(long = "test", short)]
    test: Option<String>,

    /// Random seed used in tests
    #[clap(long, short, default_value = "123")]
    seed: u64,
}

// MAIN ----------------------------------------------------------------------------------------------------------------

fn main() {
    let args = Args::parse();
    if args.impl_path.ends_with(".py") {
        env::set_var("PYTHONPATH", "../");
    }
    init_logger(LevelFilter::Debug);
    let config = TestConfig {
        impl_path: args.impl_path,
        seed: args.seed,
    };

    let mut tests = TestSuite::new();
    tests.add("RUN", test_run, config.clone());
    tests.add("RESULT", test_result, config.clone());
    tests.add("RESULT UNRELIABLE", test_result_unreliable, config.clone());
    tests.add(
        "10 RESULTS UNRELIABLE",
        test_10_results_unreliable,
        config.clone(),
    );
    tests.add("DROP PING", test_drop_ping, config.clone());
    tests.add("DROP PONG", test_drop_pong, config.clone());
    tests.add("DROP PING 2", test_drop_ping_2, config.clone());
    tests.add("DROP PONG 2", test_drop_pong_2, config.clone());
    tests.add("10 UNIQUE RESULTS", test_10_unique_results, config.clone());
    tests.add(
        "10 UNIQUE RESULTS UNRELIABLE",
        test_10_unique_results_unreliable,
        config.clone(),
    );
    tests.add(
        "MC RELIABLE NETWORK",
        test_mc_reliable_network,
        config.clone(),
    );
    tests.add(
        "MC UNRELIABLE NETWORK",
        test_mc_unreliable_network,
        config.clone(),
    );
    tests.add(
        "MC LIMITED MESSAGE DROPS",
        test_mc_limited_message_drops,
        config.clone(),
    );
    tests.add(
        "MC CONSECUTIVE MESSAGES",
        test_mc_consecutive_messages,
        config,
    );

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap().to_uppercase().replace("_", " "));
    }
}

// UTILS ---------------------------------------------------------------------------------------------------------------

#[derive(Clone)]
struct TestConfig {
    impl_path: String,
    seed: u64,
}

fn init_logger(level: LevelFilter) {
    Builder::new()
        .filter(Some("dslab_mp"), level)
        .format(|buf, record| writeln!(buf, "{}", record.args()))
        .init();
}

fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    sys.add_node("server-node");
    sys.add_node("client-node");
    let server_f = PyProcessFactory::new(&config.impl_path, "PingServer");
    let server = server_f.build(("server",), config.seed);
    let client_f = PyProcessFactory::new(&config.impl_path, "PingClient");
    let client = client_f.build(("client", "server"), config.seed);
    sys.add_process("server", boxed!(server), "server-node");
    sys.add_process("client", boxed!(client), "client-node");
    sys
}

fn check(messages: Vec<Message>, expected: &str) -> TestResult {
    assume!(!messages.is_empty(), "No messages returned by the client")?;
    assume!(
        messages.len() == 1,
        format!("Wrong number of messages: {}", messages.len())
    )?;
    let m = &messages[0];
    assume!(m.tip == "PONG", format!("Wrong message type: {}", m.tip))?;
    assume!(
        m.data == expected,
        format!("Wrong message data: {}, expected: {}", m.data, expected)
    )?;
    Ok(true)
}

// TESTS ---------------------------------------------------------------------------------------------------------------

fn test_run(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let msg = Message::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local_message("client", msg);
    sys.step_until_no_events();
    Ok(true)
}

fn test_result(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_result_unreliable(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_drop_rate(0.5);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_10_results_unreliable(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_drop_rate(0.5);
    let data = r#"{"value": "Hello!"}"#;
    for _ in 0..10 {
        sys.send_local_message("client", Message::new("PING", data));
        sys.step_until_no_events();
        check(sys.read_local_messages("client"), data)?;
    }
    Ok(true)
}

fn test_drop_ping(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_drop_rate(1.0);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().set_drop_rate(0.0);
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_drop_pong(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.network().set_drop_rate(1.0);
    sys.steps(10);
    sys.network().set_drop_rate(0.0);
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_drop_ping_2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().drop_outgoing("client-node");
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().pass_outgoing("client-node");
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_drop_pong_2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().drop_outgoing("server-node");
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().pass_outgoing("server-node");
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

fn test_10_unique_results(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_delays(1.0, 2.0);
    for i in 0..10 {
        let data = format!(r#"{{"value": "Hello{}!"}}"#, i);
        sys.send_local_message("client", Message::new("PING", &data));
        let messages = sys.step_until_local_message("client")?;
        check(messages, &data)?;
    }
    Ok(true)
}

fn test_10_unique_results_unreliable(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_delays(1.0, 2.0);
    sys.network().set_drop_rate(0.5);
    for i in 0..10 {
        let data = format!(r#"{{"value": "Hello{}!"}}"#, i);
        sys.send_local_message("client", Message::new("PING", &data));
        let messages = sys.step_until_local_message("client")?;
        check(messages, &data)?;
    }
    Ok(true)
}

// MODEL CHECKING ------------------------------------------------------------------------------------------------------

fn test_mc_reliable_network(config: &TestConfig) -> TestResult {
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

fn test_mc_unreliable_network(config: &TestConfig) -> TestResult {
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

fn test_mc_limited_message_drops(config: &TestConfig) -> TestResult {
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

fn test_mc_consecutive_messages(config: &TestConfig) -> TestResult {
    let sys = build_system(config);
    let data = r#"{"value": 0}"#.to_string();
    let data2 = r#"{"value": 1}"#.to_string();

    let messages_data = vec![data, data2];
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
