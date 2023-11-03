use serde::Deserialize;

#[derive(Deserialize)]
pub struct Config {
    pub balancer: String,
    pub n_balancers: u32,
    pub sync_interval: f64,
}
