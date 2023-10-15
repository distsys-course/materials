use serde::{Deserialize, Serialize};
use sugars::boxed;

use dslab_mp::system::System;
use dslab_mp_python::PyProcessFactory;

#[derive(Serialize)]
pub struct JoinMessage<'a> {
    pub seed: &'a str,
}

#[derive(Serialize)]
pub struct LeaveMessage {}

#[derive(Serialize)]
pub struct GetMembersMessage {}

#[derive(Deserialize)]
pub struct MembersMessage {
    pub members: Vec<String>,
}

#[derive(Clone, Copy)]
pub struct TestConfig<'a> {
    pub process_factory: &'a PyProcessFactory,
    pub process_count: u32,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    sys.network().set_delays(0.01, 0.1);
    for n in 0..config.process_count {
        // process and node on which it runs have the same name
        let name = format!("{}", &n);
        sys.add_node(&name);
        let clock_skew = sys.gen_range(0.0..10.0);
        sys.set_node_clock_skew(&name, clock_skew);
        let process = config.process_factory.build((&name,), config.seed);
        sys.add_process(&name, boxed!(process), &name);
    }
    sys
}
