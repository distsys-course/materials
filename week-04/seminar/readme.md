# 04. Групповые взаимодействия (план семинара)

## IP Multicast

- Гарантии.
- Адресация: IP-адреса [класса D](https://en.wikipedia.org/wiki/Multicast_address).
- Управление multicast-группами: [протокол IGMP](https://linkmeup.gitbook.io/sdsm/9.-multicast/1.-igmp).
- [Пример использования](./ip_multicast/).
- Применение: [zeroconf](https://en.wikipedia.org/wiki/Zero-configuration_networking), [multicast DNS](https://en.wikipedia.org/wiki/Multicast_DNS), [multicast NTP](https://www.oreilly.com/library/view/cisco-ios-cookbook/0596527225/ch14s11.html), [node discovery](https://ignite.apache.org/docs/latest/clustering/tcp-ip-discovery).
- Почему вне локальной сети не распространено?

Более подробный материал [тут](https://linkmeup.gitbook.io/sdsm/9.-multicast).

## Reliable broadcast

- Гарантии: Validity, No Duplication, No Creation, Agreement, Uniform Agreement (презентация, слайды 21 и 28).
- Примеры (презентация, слайд 22).

## Порядок

- Почему нет глобального порядка по времени?
- Отношение [happens-before](https://en.wikipedia.org/wiki/Happened-before).
- FIFO, Causal, Total Order (презентация, слайды 30-33).

Подробный материал [тут](https://www.cl.cam.ac.uk/teaching/2021/ConcDisSys/dist-sys-notes.pdf), разделы 3 и 4.

## Gossip

- Push, pull, push-pull
- [Визуализация](https://flopezluis.github.io/gossip-simulator/)
- [Лаба](./gossip/)
- Использование: состояние нод и group membersip ([раз](https://developer.hashicorp.com/consul/docs/architecture/gossip), [два](https://www.hashicorp.com/resources/everybody-talks-gossip-serf-memberlist-raft-swim-hashicorp-consul), [три](https://docs.datastax.com/en/cassandra-oss/3.x/cassandra/architecture/archGossipAbout.html), также см. шестой семинар), распространение блоков и транзакций в Bitcoin ([раз](https://nakamoto.com/bitcoins-p2p-network/), [два](https://arxiv.org/pdf/1703.08761.pdf), [три (видео)](https://www.dsn.kastel.kit.edu/bitcoin/videos.html)).
