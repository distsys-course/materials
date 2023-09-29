use std::env;

use clap::Parser;
use serde::Serialize;
use sugars::boxed;

use dslab_mp::message::Message;
use dslab_mp::system::System;
use dslab_mp_python::PyProcessFactory;

// CLI -----------------------------------------------------------------------------------------------------------------

/// Gossip simulator.
#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    /// Path to Python file with process implementations.
    #[clap(long = "impl", short)]
    impl_path: String,

    /// Number of nodes.
    #[clap(long, short, default_value = "10")]
    nodes: u32,

    /// Network drop rate.
    #[clap(long, short, default_value = "0")]
    drop_rate: f64,

    /// Fan-out (how many peers to contact on each round).
    #[clap(long, short, default_value = "1")]
    fanout: u32,

    /// Stop simulation when all nodes delivered info.
    #[clap(long, short)]
    quick_mode: bool,

    /// Time limit in simulation.
    #[clap(long, short, default_value = "60")]
    time_limit: u32,

    /// Random seed.
    #[clap(long, short, default_value = "123")]
    seed: u64,
}

// MAIN ----------------------------------------------------------------------------------------------------------------

fn main() {
    let args = Args::parse();
    env::set_var("PYTHONPATH", "../");
    env::set_var("PYTHONHASHSEED", args.seed.to_string());
    let proc_factory = PyProcessFactory::new(&args.impl_path, "Peer");
    println!("Nodes: {}", args.nodes);
    println!("Fanout: {}", args.fanout);
    println!("Network drop rate: {}", args.drop_rate);
    println!("Implementation: {}", args.impl_path);

    let mut sys = build_system(
        proc_factory,
        args.nodes,
        args.drop_rate,
        args.fanout,
        args.seed,
    );
    sys.send_local_message(
        "0",
        Message::json(
            "BROADCAST",
            &BroadcastMessage {
                info: "Some very important information to propagate to all nodes",
            },
        ),
    );
    println!(
        "\n{:<10} {:<12} {:<12} {:<12}",
        "time", "delivered", "stopped", "messages"
    );
    loop {
        let more_events = sys.step_for_duration(1.);
        let (delivered, stopped) = get_stats(&sys);
        println!(
            "{:<10} {:<12} {:<12} {:<12}",
            sys.time(),
            delivered,
            stopped,
            sys.network().network_message_count()
        );
        if !more_events
            || (args.quick_mode && delivered == args.nodes)
            || sys.time() >= args.time_limit as f64
        {
            break;
        }
    }
    let sent_counts: Vec<u64> = sys
        .process_names()
        .iter()
        .map(|p| sys.sent_message_count(&p))
        .collect();
    println!(
        "\nMessages sent by each node: max={}, min={}, mean={:.2}",
        sent_counts.iter().max().unwrap(),
        sent_counts.iter().min().unwrap(),
        sent_counts.iter().sum::<u64>() as f64 / sent_counts.len() as f64
    )
}

// UTILS ---------------------------------------------------------------------------------------------------------------

#[derive(Serialize)]
struct StartMessage {}

#[derive(Serialize)]
struct BroadcastMessage<'a> {
    info: &'a str,
}

fn build_system(
    proc_factory: PyProcessFactory,
    nodes: u32,
    drop_rate: f64,
    fanout: u32,
    seed: u64,
) -> System {
    let mut sys = System::new(seed);
    sys.network().set_delay(0.1);
    sys.network().set_drop_rate(drop_rate);
    for proc_id in 0..nodes {
        // process and node on which it runs have the same name
        let name = format!("{}", &proc_id);
        sys.add_node(&name);
        let proc = proc_factory.build((proc_id, nodes, fanout), seed);
        sys.add_process(&name, boxed!(proc), &name);
        sys.send_local_message(&name, Message::json("START", &StartMessage {}))
    }
    sys
}

fn get_stats(sys: &System) -> (u32, u32) {
    let mut delivered_count = 0;
    let mut stopped_count = 0;
    for proc in sys.process_names() {
        let outbox = sys.local_outbox(&proc);
        let msg_count = outbox.len();
        if msg_count > 0 {
            assert_eq!(outbox.get(0).unwrap().tip, "DELIVER");
            delivered_count += 1;
        }
        if msg_count == 2 {
            assert_eq!(outbox.get(1).unwrap().tip, "STOPPED");
            stopped_count += 1;
        }
        assert!(msg_count <= 2);
    }
    (delivered_count, stopped_count)
}
