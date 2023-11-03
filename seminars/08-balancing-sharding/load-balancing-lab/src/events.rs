use serde::Serialize;

#[derive(Clone, Serialize)]
pub struct SyncEvent {}

#[derive(Clone, Serialize)]
pub struct RequestArrivalEvent {
    pub processing_time: f64,
    pub sender: usize,
}

#[derive(Clone, Serialize)]
pub struct RequestEndEvent {}
