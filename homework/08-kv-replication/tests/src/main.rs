mod common;
mod tests;
mod tests_mc;

use std::env;
use std::io::Write;

use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;
use rand::prelude::*;

use dslab_mp::test::TestSuite;
use dslab_mp_python::PyProcessFactory;

use crate::common::TestConfig;
use crate::tests::*;
use crate::tests_mc::*;

/// Replicated KV Store Homework Tests
#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    /// Path to Python file with solution
    #[clap(long = "impl", short = 'i', default_value = "../solution.py")]
    solution_path: String,

    /// Test to run (optional)
    #[clap(long = "test", short)]
    test: Option<String>,

    /// Print execution trace
    #[clap(long, short)]
    debug: bool,

    /// Number of nodes used in tests
    #[clap(long, short, default_value = "6")]
    node_count: u32,

    /// Random seed used in tests
    #[clap(long, short, default_value = "123")]
    seed: u64,
}

fn main() {
    let args = Args::parse();
    if args.debug {
        Builder::new()
            .filter(Some("dslab_mp"), LevelFilter::Debug)
            .format(|buf, record| writeln!(buf, "{}", record.args()))
            .init();
    }
    env::set_var("PYTHONPATH", "../../dslab");
    env::set_var("PYTHONHASHSEED", args.seed.to_string());
    let proc_factory = PyProcessFactory::new(&args.solution_path, "StorageNode");
    let config = TestConfig {
        proc_factory: &proc_factory,
        proc_count: args.node_count,
        seed: args.seed,
    };

    let mut tests = TestSuite::new();
    tests.add("BASIC", test_basic, config);
    tests.add("REPLICAS CHECK", test_replicas_check, config);
    tests.add("MC BASIC", test_mc_basic, config);
    tests.add("CONCURRENT WRITES", test_concurrent_writes, config);
    tests.add("CONCURRENT WRITES TIE", test_concurrent_writes_tie, config);
    tests.add("MC CONCURRENT WRITES", test_mc_concurrent_writes, config);
    tests.add("STALE REPLICA", test_stale_replica, config);
    tests.add("STALE REPLICA DELETE", test_stale_replica_delete, config);
    tests.add("DIVERGED REPLICAS", test_diverged_replicas, config);
    tests.add("SLOPPY QUORUM READ", test_sloppy_quorum_read, config);
    tests.add("SLOPPY QUORUM WRITE", test_sloppy_quorum_write, config);
    tests.add("SLOPPY QUORUM TRICKY", test_sloppy_quorum_tricky, config);
    tests.add(
        "MC SLOPPY QUORUM HINTED HANDOFF",
        test_mc_sloppy_quorum_hinted_handoff,
        config,
    );
    tests.add("PARTITION CLIENTS", test_partition_clients, config);
    tests.add("PARTITION MIXED", test_partition_mixed, config);

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap());
    }
}
