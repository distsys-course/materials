mod common;
mod tests;
mod tests_mc;

use std::env;
use std::io::Write;

use clap::Parser;
use env_logger::Builder;
use log::LevelFilter;
use rand::prelude::*;
use rand_pcg::Pcg64;

use dslab_mp::test::TestSuite;
use dslab_mp_python::PyProcessFactory;

use crate::common::TestConfig;
use crate::tests::*;
use crate::tests_mc::*;

/// Membership Homework Tests
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

    /// Random seed used in tests
    #[clap(long, short, default_value = "123")]
    seed: u64,

    /// Number of processes
    #[clap(long, short, default_value = "10")]
    process_count: u32,

    /// Number of chaos monkey runs
    #[clap(long, short, default_value = "100")]
    monkeys: u32,

    /// Do not run model checking tests
    #[clap(long)]
    disable_mc_tests: bool,
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
    let process_factory = PyProcessFactory::new(&args.solution_path, "GroupMember");
    let mut config = TestConfig {
        process_factory: &process_factory,
        process_count: args.process_count,
        seed: args.seed,
    };
    let mut tests = TestSuite::new();

    tests.add("SIMPLE", test_simple, config);
    tests.add("GET MEMBERS SEMANTICS", test_get_members_semantics, config);
    tests.add("RANDOM SEED", test_random_seed, config);
    tests.add("PROCESS JOIN", test_process_join, config);
    tests.add("PROCESS LEAVE", test_process_leave, config);
    tests.add("PROCESS CRASH", test_process_crash, config);
    tests.add("SEED PROCESS CRASH", test_seed_process_crash, config);
    tests.add("PROCESS CRASH RECOVER", test_process_crash_recover, config);
    tests.add("PROCESS OFFLINE", test_process_offline, config);
    tests.add("SEED PROCESS OFFLINE", test_seed_process_offline, config);
    tests.add(
        "PROCESS OFFLINE RECOVER",
        test_process_offline_recover,
        config,
    );
    tests.add(
        "PROCESS CANNOT RECEIVE",
        test_process_cannot_receive,
        config,
    );
    tests.add("PROCESS CANNOT SEND", test_process_cannot_send, config);
    tests.add("NETWORK PARTITION", test_network_partition, config);
    tests.add(
        "NETWORK PARTITION RECOVER",
        test_network_partition_recover,
        config,
    );
    tests.add(
        "TWO PROCESSES CANNOT COMMUNICATE",
        test_two_processes_cannot_communicate,
        config,
    );
    tests.add("SLOW NETWORK", test_slow_network, config);
    tests.add("FLAKY NETWORK", test_flaky_network, config);
    tests.add(
        "FLAKY NETWORK ON START",
        test_flaky_network_on_start,
        config,
    );
    tests.add(
        "FLAKY NETWORK AND CRASH",
        test_flaky_network_and_crash,
        config,
    );
    let mut rand = Pcg64::seed_from_u64(config.seed);
    for run in 1..=args.monkeys {
        let mut run_config = config;
        run_config.seed = rand.next_u64();
        tests.add(
            &format!("CHAOS MONKEY (run {})", run),
            test_chaos_monkey,
            run_config,
        );
    }
    tests.add("SCALABILITY NORMAL", test_scalability_normal, config);
    tests.add("SCALABILITY CRASH", test_scalability_crash, config);

    if !args.disable_mc_tests {
        config.process_count = 3;
        tests.add("MODEL CHECKING", test_mc_group, config);
    }

    if args.test.is_none() {
        tests.run();
    } else {
        tests.run_test(&args.test.unwrap());
    }
}
