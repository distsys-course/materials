use std::boxed::Box;
use std::cell::RefCell;
use std::rc::Rc;

use rand::prelude::*;
use rand_pcg::Pcg64;

use dslab_core::cast;
use dslab_core::context::SimulationContext;
use dslab_core::event::Event;
use dslab_core::handler::EventHandler;

use crate::events::{RequestArrivalEvent, SyncEvent};
use crate::host::Host;

#[derive(Copy, Clone)]
pub struct HostSnapshot {
    pub id: usize,
    pub requests: usize,
}

pub struct LoadBalancer {
    state: Vec<HostSnapshot>,
    hosts: Vec<Rc<RefCell<Host>>>,
    selector: Box<dyn HostSelector>,
    sync_interval: f64,
    ctx: Rc<RefCell<SimulationContext>>
}

impl LoadBalancer {
    pub fn new(hosts: Vec<Rc<RefCell<Host>>>, selector: Box<dyn HostSelector>, sync_interval: f64, ctx: Rc<RefCell<SimulationContext>>) -> Self {
        Self {
            state: (0..hosts.len()).map(|i| HostSnapshot{id: i, requests: 0}).collect(),
            hosts,
            selector,
            sync_interval,
            ctx,
        }
    }
}

impl EventHandler for LoadBalancer {
    fn on(&mut self, event: Event) {
        cast!(match event.data {
            RequestArrivalEvent { processing_time, sender } => {
                let host = self.selector.select(&self.state, &self.hosts, sender);
                self.hosts[host.id].borrow_mut().on_new_request(processing_time, event.time);
            }
            SyncEvent {} => {
                for (i, host) in self.hosts.iter().enumerate() {
                    self.state[i].requests = host.borrow().requests.len();
                }
                self.ctx.borrow_mut().emit_self(SyncEvent {}, self.sync_interval);
            }
        });
    }
}

pub trait HostSelector {
    fn select(&mut self, states: &[HostSnapshot], hosts: &[Rc<RefCell<Host>>], sender: usize) -> HostSnapshot;
}

#[derive(Default)]
pub struct RoundRobinSelector {
    pub ptr: usize,
}

impl HostSelector for RoundRobinSelector {
    fn select(&mut self, states: &[HostSnapshot], hosts: &[Rc<RefCell<Host>>], _sender: usize) -> HostSnapshot {
        let id = self.ptr;
        self.ptr += 1;
        if self.ptr == hosts.len() {
            self.ptr = 0;
        }
        states[id]
    }
}

pub struct RandomSelector {
    rng: Pcg64,
}

impl Default for RandomSelector {
    fn default() -> Self {
        Self { rng: Pcg64::seed_from_u64(111) }
    }
}

impl HostSelector for RandomSelector {
    fn select(&mut self, states: &[HostSnapshot], _hosts: &[Rc<RefCell<Host>>], _sender: usize) -> HostSnapshot {
        *states.choose(&mut self.rng).unwrap()
    }
}

pub struct LeastLoadedSelector {}

impl HostSelector for LeastLoadedSelector {
    fn select(&mut self, states: &[HostSnapshot], _hosts: &[Rc<RefCell<Host>>], _sender: usize) -> HostSnapshot {
        *states.iter().min_by_key(|s| s.requests).unwrap()
    }
}

pub struct PowerOfKSelector {
    k: usize,
    rng: Pcg64,
}

impl PowerOfKSelector {
    pub fn new(k: usize) -> Self {
        Self { k, rng: Pcg64::seed_from_u64(111) }
    }
}

impl HostSelector for PowerOfKSelector {
    fn select(&mut self, states: &[HostSnapshot], _hosts: &[Rc<RefCell<Host>>], _sender: usize) -> HostSnapshot {
        **states.iter().choose_multiple(&mut self.rng, self.k).iter().min_by_key(|s| s.requests).unwrap()
    }
}

pub struct PowerOfKSelectorWithUpdates {
    k: usize,
    rng: Pcg64,
}

impl PowerOfKSelectorWithUpdates {
    pub fn new(k: usize) -> Self {
        Self { k, rng: Pcg64::seed_from_u64(111) }
    }
}

impl HostSelector for PowerOfKSelectorWithUpdates {
    fn select(&mut self, states: &[HostSnapshot], hosts: &[Rc<RefCell<Host>>], _sender: usize) -> HostSnapshot {
        **states.iter().choose_multiple(&mut self.rng, self.k).iter().min_by_key(|s| hosts[s.id].borrow().requests.len()).unwrap()
    }
}

pub struct HashSelector {}

impl HostSelector for HashSelector {
    fn select(&mut self, states: &[HostSnapshot], _hosts: &[Rc<RefCell<Host>>], sender: usize) -> HostSnapshot {
        states[sender % states.len()]
    }
}

pub fn create_selector_by_name(name: &str) -> Box<dyn HostSelector> {
    match name {
        "RoundRobin" => {
            Box::new(RoundRobinSelector::default())
        },
        "Random" => {
            Box::new(RandomSelector::default())
        },
        "LeastLoaded" => {
            Box::new(LeastLoadedSelector{})
        },
        "Hash" => {
            Box::new(HashSelector{})
        },
        _ => {
            if name.starts_with("PowerOfK[k=") && name.ends_with("]") {
                let k = name[11..name.len() - 1].parse::<usize>().unwrap();
                Box::new(PowerOfKSelector::new(k))
            } else if name.starts_with("PowerOfKWithUpdates[k=") && name.ends_with("]") {
                let k = name[22..name.len() - 1].parse::<usize>().unwrap();
                Box::new(PowerOfKSelectorWithUpdates::new(k))
            } else {
                panic!("Unknown host selector: {}", name);
            }
        },
    }
}
