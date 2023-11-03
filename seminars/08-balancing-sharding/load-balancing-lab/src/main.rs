use std::cell::RefCell;
use std::collections::BTreeSet;
use std::fs::File;
use std::io::prelude::*;
use std::io::BufWriter;
use std::path::Path;
use std::rc::Rc;

use clap::Parser;
use rand::prelude::*;
use rand_distr::Exp;
use rand_pcg::Pcg64;

use dslab_core::simulation::Simulation;

mod balancer;
mod config;
mod events;
mod host;
mod log;

use crate::balancer::{LoadBalancer, create_selector_by_name};
use crate::config::Config;
use crate::events::{RequestArrivalEvent, SyncEvent};
use crate::host::Host;
use crate::log::{EventLog, LogEntry};

#[derive(Parser, Debug)]
#[clap(about, long_about = None)]
struct Args {
    /// Results dump path.
    #[clap(long)]
    dump: String,

    /// Configuration JSON file.
    #[clap(long)]
    config: String,

    /// Number of servers.
    #[clap(long, default_value = "100")]
    servers: u32,

    /// Time limit in seconds.
    #[clap(long, default_value = "3600")]
    time_limit: f64,

    /// Number of senders generating requests.
    #[clap(long, default_value = "200")]
    senders: u32,

    /// Load distribution preset (balanced/skewed).
    #[clap(long, default_value = "balanced")]
    preset: String,

    /// Adds slower servers to simulate heterogenous cluster.
    #[clap(long)]
    different_servers: bool,

    /// Random seed.
    #[clap(long, default_value = "123")]
    seed: u64,
}

fn run_simulation(args: &Args, config: &Config) -> Vec<(f64, usize)> {
    let mut sim = Simulation::new(args.seed);
    let ctx = sim.create_context("entry point");
    let log = Rc::new(RefCell::new(EventLog::new()));
    let mut hosts = Vec::with_capacity(args.servers as usize);
    for i in 0..args.servers {
        let slowdown = if args.different_servers && i < args.servers / 20 { 5.0 } else { 1.0 };
        hosts.push(Rc::new(RefCell::new(Host::new(i as usize, slowdown, log.clone(), Rc::new(RefCell::new(sim.create_context(format!("host_{}", i))))))));
        sim.add_handler(format!("host_{}", i), hosts[i as usize].clone());
    }
    let mut balancers = Vec::with_capacity(config.n_balancers as usize);
    for i in 0..config.n_balancers {
        balancers.push(Rc::new(RefCell::new(LoadBalancer::new(hosts.clone(), create_selector_by_name(&config.balancer), config.sync_interval, Rc::new(RefCell::new(sim.create_context(format!("balancer_{}", i))))))));
        sim.add_handler(format!("balancer_{}", i), balancers[i as usize].clone());
        ctx.emit(SyncEvent {}, sim.lookup_id(&format!("balancer_{}", i)), 0.0);
    }
    let mut rng = Pcg64::seed_from_u64(args.seed);
    for sender in 0..(args.senders as usize) {
        let distr = Exp::new(if args.preset == "skewed" && sender == 0 { 50.0 } else { 1.0 }).unwrap();
        let mut t = 0f64;
        loop {
            t += distr.sample(&mut rng);
            if t > args.time_limit {
                break;
            }
            let processing_time = rng.gen_range(0.5..2.5);
            ctx.emit(RequestArrivalEvent { processing_time, sender }, sim.lookup_id(&format!("balancer_{}", rng.gen_range(0..balancers.len()))), t);
        }
    }
    sim.step_for_duration(args.time_limit);
    let mut result = Vec::new();
    let mut load = vec![0; hosts.len()];
    let mut load_set: BTreeSet<(usize, usize)> = (0..hosts.len()).map(|x| (0, x)).collect();
    for entry in log.borrow().iter().copied() {
        match entry.1 {
            LogEntry::Arrival(host) => {
                load_set.remove(&(load[host], host));
                load[host] += 1;
                load_set.insert((load[host], host));
            }
            LogEntry::Departure(host) => {
                load_set.remove(&(load[host], host));
                load[host] -= 1;
                load_set.insert((load[host], host));
            }
        }
        result.push((entry.0, load_set.last().unwrap().0));
    }
    result
}

fn main() {
    let args = Args::parse();
    let configs: Vec<Config> = serde_json::from_reader(File::open(Path::new(&args.config)).unwrap()).unwrap();
    let mut out = BufWriter::new(File::create(&args.dump).unwrap());
    for config in configs.iter() {
        let result = run_simulation(&args, config);
        out.write(config.balancer.as_bytes()).unwrap();
        out.write(b"\n").unwrap();
        out.write(result.iter().map(|x| format!("{:.3}", x.0)).collect::<Vec<_>>().join(",").as_bytes()).unwrap();
        out.write(b"\n").unwrap();
        out.write(result.iter().map(|x| format!("{}", x.1)).collect::<Vec<_>>().join(",").as_bytes()).unwrap();
        out.write(b"\n").unwrap();
    }
    out.flush().unwrap();
}
