use std::cell::RefCell;
use std::collections::VecDeque;
use std::rc::Rc;

use dslab_core::cast;
use dslab_core::context::SimulationContext;
use dslab_core::event::Event;
use dslab_core::handler::EventHandler;

use crate::events::RequestEndEvent;
use crate::log::{EventLog, LogEntry};

pub struct Host {
    pub id: usize,
    pub requests: VecDeque<f64>,
    slowdown: f64,
    log: Rc<RefCell<EventLog>>,
    ctx: Rc<RefCell<SimulationContext>>,
}

impl Host {
    pub fn new(id: usize, slowdown: f64, log: Rc<RefCell<EventLog>>, ctx: Rc<RefCell<SimulationContext>>) -> Self {
        Self {
            id,
            requests: Default::default(),
            slowdown,
            log,
            ctx,
        }
    }

    pub fn on_new_request(&mut self, duration: f64, time: f64) {
        self.requests.push_back(duration * self.slowdown);
        self.log.borrow_mut().push((time, LogEntry::Arrival(self.id)));
        if self.requests.len() == 1 {
            self.ctx.borrow_mut().emit_self(RequestEndEvent {}, duration * self.slowdown);
        }
    }
}

impl EventHandler for Host {
    fn on(&mut self, event: Event) {
        cast!(match event.data {
            RequestEndEvent {} => {
                self.requests.pop_front();
                self.log.borrow_mut().push((event.time, LogEntry::Departure(self.id)));
                if let Some(delay) = self.requests.front() {
                    self.ctx.borrow_mut().emit_self(RequestEndEvent {}, *delay);
                }
            }
        });
    }
}
