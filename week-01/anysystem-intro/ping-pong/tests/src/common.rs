use assertables::assume;
use sugars::boxed;

use anysystem::python::PyProcessFactory;
use anysystem::test::TestResult;
use anysystem::{Message, System};

#[derive(Clone)]
pub struct TestConfig {
    pub impl_path: String,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig) -> System {
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

pub fn check(messages: Vec<Message>, expected: &str) -> TestResult {
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
