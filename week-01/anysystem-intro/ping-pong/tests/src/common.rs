use assertables::assume;
use sugars::boxed;

use anysystem::python::PyProcessFactory;
use anysystem::test::TestResult;
use anysystem::{Message, Process, System};

use crate::solution::{basic, retry, TestLanguage, LANGUAGE};

#[derive(Clone)]
pub struct TestConfig {
    pub impl_path: String,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    sys.add_node("server-node");
    sys.add_node("client-node");
    let (server, client): (Box<dyn Process>, Box<dyn Process>) = match LANGUAGE {
        TestLanguage::Python => {
            let server_f = PyProcessFactory::new(&config.impl_path, "PingServer");
            let server = server_f.build(("server",), config.seed);
            let client_f = PyProcessFactory::new(&config.impl_path, "PingClient");
            let client = client_f.build(("client", "server"), config.seed);
            (boxed!(server), boxed!(client))
        }
        TestLanguage::Rust => match () {
            () if config.impl_path.contains("basic") => (
                boxed!(basic::Server::new()),
                boxed!(basic::Client::new("server")),
            ),
            () if config.impl_path.contains("retry") => (
                boxed!(retry::Server::new()),
                boxed!(retry::Client::new("server")),
            ),
            () => unreachable!(),
        },
    };
    sys.add_process("server", server, "server-node");
    sys.add_process("client", client, "client-node");
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
