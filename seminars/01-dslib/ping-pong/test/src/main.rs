use std::env;
use std::io::Write;

use assertables::assume;
use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;
use sugars::{rc, refcell};

use dslib::node::LocalEventType;
use dslib::pynode::{JsonMessage, PyNodeFactory};
use dslib::system::System;
use dslib::test::{TestResult, TestSuite};

// UTILS -------------------------------------------------------------------------------------------

#[derive(Copy, Clone)]
struct TestConfig<'a> {
    client_f: &'a PyNodeFactory,
    server_f: &'a PyNodeFactory,
    seed: u64,
    drop_rate: f64,
}

fn init_logger(level: LevelFilter) {
    Builder::new()
        .filter(None, level)
        .format(|buf, record| writeln!(buf, "{}", record.args()))
        .init();
}

fn build_system(config: &TestConfig) -> System<JsonMessage> {
    let mut sys = System::with_seed(config.seed);
    let client = config
        .client_f
        .build("client", ("client", "server"), config.seed);
    sys.add_node(rc!(refcell!(client)));
    let server = config.server_f.build("server", ("server",), config.seed);
    sys.add_node(rc!(refcell!(server)));
    return sys;
}

fn get_local_messages(sys: &System<JsonMessage>, node: &str) -> Vec<JsonMessage> {
    sys.get_local_events(node)
        .into_iter()
        .filter(|m| matches!(m.tip, LocalEventType::LocalMessageSend))
        .map(|m| m.msg.unwrap())
        .collect::<Vec<_>>()
}

// TESTS -------------------------------------------------------------------------------------------

fn test_run(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.step_until_no_events();
    Ok(true)
}

fn test_result(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.set_drop_rate(config.drop_rate);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.step_until_no_events();
    let messages = get_local_messages(&sys, "client");
    assume!(messages.len() > 0, "No messages returned by client!")?;
    assume!(messages.len() == 1, "More than one message???")?;
    for m in messages {
        assume!(m.tip == "PONG", "Wrong message type!")?;
        assume!(m.data == r#"{"value": "Hello!"}"#, "Wrong message data!")?;
    }
    Ok(true)
}

fn test_10results(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.set_drop_rate(config.drop_rate);
    for i in 0..10 {
        let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
        sys.send_local(ping, "client");
        sys.step_until_no_events();
        let messages = get_local_messages(&sys, "client");
        assume!(messages.len() > 0, "No messages returned by client!")?;
        assume!(messages.len() == 1 + i, "Wrong number of messages!")?;
        assume!(messages[i].tip == "PONG", "Wrong message type!")?;
        assume!(
            messages[i].data == r#"{"value": "Hello!"}"#,
            "Wrong message data!"
        )?;
    }
    Ok(true)
}

fn test_drop_ping(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.set_drop_rate(1.0);
    sys.steps(10);
    sys.set_drop_rate(0.0);
    sys.step_until_no_events();
    let messages = get_local_messages(&sys, "client");
    assume!(messages.len() > 0, "No messages returned by client!")?;
    assume!(messages.len() == 1, "More than one message???")?;
    for m in messages {
        assume!(m.tip == "PONG", "Wrong message type!")?;
        assume!(m.data == r#"{"value": "Hello!"}"#, "Wrong message data!")?;
    }
    Ok(true)
}

fn test_drop_pong(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.steps(2);
    sys.set_drop_rate(1.0);
    sys.steps(10);
    sys.set_drop_rate(0.0);
    sys.step_until_no_events();
    let messages = get_local_messages(&sys, "client");
    assume!(messages.len() > 0, "No messages returned by client!")?;
    assume!(messages.len() == 1, "More than one message???")?;
    for m in messages {
        assume!(m.tip == "PONG", "Wrong message type!")?;
        assume!(m.data == r#"{"value": "Hello!"}"#, "Wrong message data!")?;
    }
    Ok(true)
}

fn test_drop_ping2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.drop_outgoing("client");
    sys.steps(10);
    sys.pass_outgoing("client");
    sys.step_until_no_events();
    let messages = get_local_messages(&sys, "client");
    assume!(messages.len() > 0, "No messages returned by client!")?;
    assume!(messages.len() == 1, "More than one message???")?;
    for m in messages {
        assume!(m.tip == "PONG", "Wrong message type!")?;
        assume!(m.data == r#"{"value": "Hello!"}"#, "Wrong message data!")?;
    }
    Ok(true)
}

fn test_drop_pong2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let ping = JsonMessage::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local(ping, "client");
    sys.drop_outgoing("server");
    sys.steps(10);
    sys.pass_outgoing("server");
    sys.step_until_no_events();
    let messages = get_local_messages(&sys, "client");
    assume!(messages.len() > 0, "No messages returned by client!")?;
    assume!(messages.len() == 1, "More than one message???")?;
    for m in messages {
        assume!(m.tip == "PONG", "Wrong message type!")?;
        assume!(m.data == r#"{"value": "Hello!"}"#, "Wrong message data!")?;
    }
    Ok(true)
}

fn test_10results_unique(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.set_delays(1.0, 2.0);
    sys.set_drop_rate(config.drop_rate);
    for i in 0..10 {
        let data = format!(r#"{{"value": "Hello{}!"}}"#, i);
        let ping = JsonMessage::new("PING", &data);
        sys.send_local(ping, "client");
        sys.step_until_local_message("client")?;
        let messages = get_local_messages(&sys, "client");
        assume!(messages.len() > 0, "No messages returned by client!")?;
        assume!(messages.len() == 1 + i, "Wrong number of messages!")?;
        assume!(messages[i].tip == "PONG", "Wrong message type!")?;
        assume!(messages[i].data == data, "Wrong message data!")?;
    }
    Ok(true)
}

// MAIN --------------------------------------------------------------------------------------------

/// Ping-Pong Tests
#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    /// Path to Python file with nodes implementations
    #[clap(long = "impl", short = 'i', default_value = "../basic.py")]
    impl_path: String,

    /// Test to run (optional)
    #[clap(long = "test", short)]
    test: Option<String>,

    /// Random seed used in tests
    #[clap(long, short, default_value = "123")]
    seed: u64,
}

fn main() {
    let args = Args::parse();
    let test = args.test.as_deref();
    init_logger(LevelFilter::Trace);

    env::set_var("PYTHONPATH", "../../dslib/python");
    let client_f = PyNodeFactory::new(&args.impl_path, "PingClient");
    let server_f = PyNodeFactory::new(&args.impl_path, "PingServer");

    let mut config = TestConfig {
        client_f: &client_f,
        server_f: &server_f,
        seed: args.seed,
        drop_rate: 0.0,
    };

    let mut tests = TestSuite::new();
    if test.is_none() || test.unwrap() == "run" {
        tests.add("TEST RUN", test_run, config);
    }
    if test.is_none() || test.unwrap() == "result_reliable" {
        tests.add("TEST RESULT (RELIABLE)", test_result, config);
    }
    if test.is_none() || test.unwrap() == "result_unreliable" {
        config.drop_rate = 0.5;
        tests.add("TEST RESULT (UNRELIABLE)", test_result, config);
    }
    if test.is_none() || test.unwrap() == "10results_unreliable" {
        config.drop_rate = 0.5;
        tests.add("TEST 10 RESULTS (UNRELIABLE)", test_10results, config);
    }
    if test.is_some() && test.unwrap() == "drop_ping" {
        tests.add("TEST RESULT (DROP PING)", test_drop_ping, config);
    }
    if test.is_some() && test.unwrap() == "drop_pong" {
        tests.add("TEST RESULT (DROP PONG)", test_drop_pong, config);
    }
    if test.is_none() || test.unwrap() == "drop_ping2" {
        tests.add("TEST RESULT (DROP PING)", test_drop_ping2, config);
    }
    if test.is_none() || test.unwrap() == "drop_pong2" {
        tests.add("TEST RESULT (DROP PONG)", test_drop_pong2, config);
    }
    if test.is_some() && test.unwrap() == "10results_unique" {
        tests.add(
            "TEST 10 UNIQUE RESULTS (RELIABLE)",
            test_10results_unique,
            config,
        );
    }
    if test.is_some() && test.unwrap() == "10results_unique_unreliable" {
        config.drop_rate = 0.5;
        tests.add(
            "TEST 10 UNIQUE RESULTS (UNRELIABLE)",
            test_10results_unique,
            config,
        );
    }
    tests.run();
}
