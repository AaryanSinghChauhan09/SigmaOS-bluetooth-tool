#[derive(Debug, Clone)]
pub struct BluetoothDevice {
    pub mac_address: String,
    pub name: String,
    pub is_paired: bool,
}

#[derive(Debug, Default)]
pub struct BluetoothManager {
    devices: Vec<BluetoothDevice>,
}

impl BluetoothManager {
    pub fn new() -> Self { Self::default() }
    pub fn pair_device(&mut self, mac: &str, name: &str) {
        self.devices.push(BluetoothDevice {
            mac_address: mac.to_string(),
            name: name.to_string(),
            is_paired: true,
        });
    }
    pub fn is_paired(&self, mac: &str) -> bool {
        self.devices.iter().any(|d| d.mac_address == mac && d.is_paired)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_bluetooth_pairing() {
        let mut mgr = BluetoothManager::new();
        mgr.pair_device("00:11:22:33:44:55", "Wireless Headphones");
        assert!(mgr.is_paired("00:11:22:33:44:55"));
    }
}
