use serde::Serialize;
use sugars::boxed;

use dslab_mp::system::System;
use dslab_mp_python::PyProcessFactory;

#[derive(Copy, Clone)]
pub struct TestConfig<'a> {
    pub proc_factory: &'a PyProcessFactory,
    pub proc_count: u64,
    pub seed: u64,
    pub monkeys: u32,
    pub debug: bool,
}

#[derive(Serialize)]
pub struct BroadcastMessage<'a> {
    pub text: &'a str,
}

pub fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    let mut proc_names = Vec::new();
    for n in 0..config.proc_count {
        proc_names.push(format!("{}", n));
    }
    for proc_name in &proc_names {
        let proc = config
            .proc_factory
            .build((proc_name, proc_names.clone()), config.seed);
        // process and node on which it runs have the same name
        sys.add_node(proc_name);
        sys.add_process(proc_name, boxed!(proc), proc_name);
    }
    sys
}
