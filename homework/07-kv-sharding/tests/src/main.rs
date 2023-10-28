mod common;
mod tests;
mod tests_mc;

use std::env;
use std::io::Write;

use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;

use dslab_mp::test::TestSuite;
use dslab_mp_python::PyProcessFactory;

use crate::common::TestConfig;
use crate::tests::*;
use crate::tests_mc::*;

/// Sharded KV Store Homework Tests
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
    #[clap(long, short, default_value = "10")]
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
    let process_factory = PyProcessFactory::new(&args.solution_path, "StorageNode");
    let config = TestConfig {
        process_factory: &process_factory,
        proc_count: args.node_count,
        seed: args.seed,
    };
    let mut single_config = config;
    single_config.proc_count = 1;
    let mut mc_config = config;
    mc_config.proc_count = 3;
    let mut tests = TestSuite::new();

    tests.add("SINGLE NODE", test_single_node, single_config);
    tests.add("INSERTS", test_inserts, config);
    tests.add("DELETES", test_deletes, config);
    tests.add("MEMORY OVERHEAD", test_memory_overhead, config);
    tests.add("MC NORMAL", test_mc_normal, mc_config);
    tests.add("NODE ADDED", test_node_added, config);
    tests.add("NODE REMOVED", test_node_removed, config);
    tests.add(
        "NODE REMOVED AFTER CRASH",
        test_node_removed_after_crash,
        config,
    );
    tests.add("MC NODE REMOVED", test_mc_node_removed, mc_config);
    tests.add("MIGRATION", test_migration, config);
    tests.add("SCALE UP DOWN", test_scale_up_down, config);
    tests.add("DISTRIBUTION", test_distribution, config);
    tests.add(
        "DISTRIBUTION NODE ADDED",
        test_distribution_node_added,
        config,
    );
    tests.add(
        "DISTRIBUTION NODE REMOVED",
        test_distribution_node_removed,
        config,
    );

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap());
    }
}
