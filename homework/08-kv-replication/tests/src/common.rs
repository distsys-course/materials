use byteorder::{ByteOrder, LittleEndian};
use rand::distributions::WeightedIndex;
use rand::prelude::*;
use rand_pcg::Pcg64;
use serde::{Deserialize, Serialize};

use dslab_mp::system::System;
use dslab_mp_python::PyProcessFactory;

#[derive(Serialize)]
pub struct GetReqMessage<'a> {
    pub key: &'a str,
    pub quorum: u8,
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
    pub quorum: u8,
}

#[derive(Deserialize)]
pub struct PutRespMessage<'a> {
    pub key: &'a str,
    pub value: &'a str,
}

#[derive(Serialize)]
pub struct DeleteReqMessage<'a> {
    pub key: &'a str,
    pub quorum: u8,
}

#[derive(Deserialize)]
pub struct DeleteRespMessage<'a> {
    pub key: &'a str,
    pub value: Option<&'a str>,
}

#[derive(Copy, Clone)]
pub struct TestConfig<'a> {
    pub proc_factory: &'a PyProcessFactory,
    pub proc_count: u32,
    pub seed: u64,
}

pub fn build_system(config: &TestConfig) -> System {
    let mut sys = System::new(config.seed);
    sys.network().set_delays(0.01, 0.1);
    let mut proc_names = Vec::new();
    for n in 0..config.proc_count {
        proc_names.push(format!("{}", n));
    }
    for proc_name in proc_names.iter() {
        let proc = config
            .proc_factory
            .build((proc_name, proc_names.clone()), config.seed);
        // process and node on which it runs have the same name
        let node_name = proc_name.clone();
        sys.add_node(&node_name);
        sys.add_process(proc_name, Box::new(proc), &node_name);
    }
    sys
}

pub fn key_replicas(key: &str, sys: &System) -> Vec<String> {
    let proc_count = sys.process_names().len();
    let mut replicas = Vec::new();
    let hash = md5::compute(key);
    let hash128 = LittleEndian::read_u128(&hash.0);
    let mut replica = (hash128 % proc_count as u128) as usize;
    for _ in 0..3 {
        replicas.push(replica.to_string());
        replica += 1;
        if replica == proc_count {
            replica = 0;
        }
    }
    replicas
}

pub fn key_non_replicas(key: &str, sys: &System) -> Vec<String> {
    let replicas = key_replicas(key, sys);
    let mut non_replicas_pre = Vec::new();
    let mut non_replicas = Vec::new();
    let mut pre = true;
    let mut process_names = sys.process_names();
    process_names.sort();
    for proc in process_names {
        if replicas.contains(&proc) {
            pre = false;
            continue;
        }
        if pre {
            non_replicas_pre.push(proc);
        } else {
            non_replicas.push(proc);
        }
    }
    non_replicas.append(&mut non_replicas_pre);
    non_replicas
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
