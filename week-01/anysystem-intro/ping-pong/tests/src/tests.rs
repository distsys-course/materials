use anysystem::test::TestResult;
use anysystem::Message;

use crate::common::*;

pub fn test_run(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let msg = Message::new("PING", r#"{"value": "Hello!"}"#);
    sys.send_local_message("client", msg);
    sys.step_until_no_events();
    Ok(true)
}

pub fn test_result(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_result_unreliable(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_drop_rate(0.5);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_10_results_unreliable(config: &TestConfig) -> TestResult {
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

pub fn test_drop_ping(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().set_drop_rate(1.0);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().set_drop_rate(0.0);
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_drop_pong(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.network().set_drop_rate(1.0);
    sys.steps(10);
    sys.network().set_drop_rate(0.0);
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_drop_ping_2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().drop_outgoing("client-node");
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().pass_outgoing("client-node");
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_drop_pong_2(config: &TestConfig) -> TestResult {
    let mut sys = build_system(config);
    sys.network().drop_outgoing("server-node");
    let data = r#"{"value": "Hello!"}"#;
    sys.send_local_message("client", Message::new("PING", data));
    sys.steps(10);
    sys.network().pass_outgoing("server-node");
    sys.step_until_no_events();
    check(sys.read_local_messages("client"), data)
}

pub fn test_10_unique_results(config: &TestConfig) -> TestResult {
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

pub fn test_10_unique_results_unreliable(config: &TestConfig) -> TestResult {
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
