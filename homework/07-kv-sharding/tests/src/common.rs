use std::collections::HashSet;

use rand::distributions::WeightedIndex;
use rand::prelude::*;
use rand_pcg::{Lcg128Xsl64, Pcg64};
use serde::{Deserialize, Serialize};
use sugars::boxed;

use dslab_mp::system::System;
use dslab_mp_python::PyProcessFactory;

#[derive(Serialize)]
pub struct GetReqMessage<'a> {
    pub key: &'a str,
}

#[derive(Deserialize)]
pub struct GetRespMessage<'a> {
    pub key: &'a str,
    pub value: Option<&'a str>,
}

#[derive(Serialize)]
pub struct PutReqMessage<'a> {
    pub key: &'a str,
    pub value: &'a str,
}

#[derive(Deserialize)]
pub struct PutRespMessage<'a> {
    pub key: &'a str,
    pub value: &'a str,
}

#[derive(Serialize)]
pub struct DeleteReqMessage<'a> {
    pub key: &'a str,
}

#[derive(Deserialize)]
pub struct DeleteRespMessage<'a> {
    pub key: &'a str,
    pub value: Option<&'a str>,
}

#[derive(Serialize)]
pub struct EmptyMessage {}

#[derive(Serialize)]
pub struct NodeMessage<'a> {
    pub id: &'a str,
}

#[derive(Deserialize)]
pub struct DumpKeysRespMessage {
    pub keys: HashSet<String>,
}

#[derive(Deserialize)]
pub struct CountRecordsRespMessage {
    pub count: u64,
}

#[derive(Copy, Clone)]
pub struct TestConfig<'a> {
    pub process_factory: &'a PyProcessFactory,
    pub proc_count: u32,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig, measure_max_size: bool) -> System {
    let mut sys = System::new(config.seed);
    sys.network().set_delays(0.01, 0.1);
    let mut proc_names = Vec::new();
    for n in 0..config.proc_count {
        proc_names.push(format!("{}", n));
    }
    for n in 0..config.proc_count {
        let proc_name = proc_names[n as usize].clone();
        let mut proc = config
            .process_factory
            .build((proc_name.clone(), proc_names.clone()), config.seed);
        if measure_max_size {
            proc.set_max_size_freq(1000000);
        }
        // process and node on which it runs have the same name
        let node_name = proc_name.clone();
        sys.add_node(&node_name);
        sys.add_process(&proc_name, boxed!(proc), &node_name);
    }
    sys
}

pub fn add_node(name: &str, sys: &mut System, config: &TestConfig) {
    let proc_name = name.to_string();
    let mut proc_names = sys.process_names();
    proc_names.push(proc_name.clone());
    let proc = config
        .process_factory
        .build((proc_name.clone(), proc_names), config.seed);
    let node_name = proc_name.clone();
    sys.add_node(&node_name);
    sys.add_process(&proc_name, boxed!(proc), &node_name);
}

pub fn random_proc(sys: &System, rand: &mut Lcg128Xsl64) -> String {
    sys.process_names().choose(rand).unwrap().clone()
}

const SYMBOLS: [char; 36] = [
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
    't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
];
const WEIGHTS: [usize; 36] = [
    13, 16, 3, 8, 8, 5, 6, 23, 4, 8, 24, 12, 2, 1, 1, 10, 5, 8, 10, 1, 24, 3, 1, 8, 12, 22, 5, 20,
    18, 5, 5, 2, 1, 3, 16, 22,
];

pub fn random_string(length: usize, rand: &mut Pcg64) -> String {
    let dist = WeightedIndex::new(WEIGHTS).unwrap();
    rand.sample_iter(&dist)
        .take(length)
        .map(|x| SYMBOLS[x])
        .collect()
}
