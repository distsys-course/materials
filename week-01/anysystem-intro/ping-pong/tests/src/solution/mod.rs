/// Language to use
/// Change to `Rust` to test rust implementation
pub const LANGUAGE: TestLanguage = TestLanguage::Python;

#[allow(dead_code)]
pub enum TestLanguage {
    Python,
    Rust,
}

pub mod basic;
pub mod retry;
