#[derive(Copy, Clone)]
pub enum LogEntry {
    Arrival(usize),
    Departure(usize),
}

pub type EventLog = Vec<(f64, LogEntry)>;
