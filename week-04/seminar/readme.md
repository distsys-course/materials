# 04. Групповые взаимодействия (план семинара)

## IP Multicast

- Гарантии.
- Адресация: IP-адреса [класса D](https://en.wikipedia.org/wiki/Multicast_address).
- Управление multicast-группами: [протокол IGMP](https://linkmeup.gitbook.io/sdsm/9.-multicast/1.-igmp).
- Программирование: [работа с multicast в Python](https://pymotw.com/3/socket/multicast.html), [пример](ip_multicast/readme.md).
- Применение: [zeroconf](https://en.wikipedia.org/wiki/Zero-configuration_networking), [multicast DNS](https://en.wikipedia.org/wiki/Multicast_DNS), [multicast NTP](https://www.oreilly.com/library/view/cisco-ios-cookbook/0596527225/ch14s11.html), [node discovery](https://ignite.apache.org/docs/latest/clustering/tcp-ip-discovery).
- Почему вне локальной сети не распространено?

Более подробный материал [тут](https://linkmeup.gitbook.io/sdsm/9.-multicast).

## Reliable broadcast

- Гарантии: Validity, No Duplication, No Creation, Agreement, Uniform Agreement ([лекция](../04-group.pdf), слайды 21 и 28).
- Примеры ([лекция](../04-group.pdf), слайд 22).

## Порядок

- Почему нет глобального порядка по времени?
- Отношение [happens-before](https://en.wikipedia.org/wiki/Happened-before).
- FIFO, Causal, Total Order ([лекция](../04-group.pdf), слайды 30-33).

Подробный материал [тут](https://www.cl.cam.ac.uk/teaching/2021/ConcDisSys/dist-sys-notes.pdf), разделы 3 и 4.

## Gossip

- Push, pull, push-pull
- [Визуализация](https://flopezluis.github.io/gossip-simulator/)
- [Лаба](gossip/readme.md)
- Использование: состояние нод, discovery и group membership ([раз](https://developer.hashicorp.com/consul/docs/architecture/gossip), [два](https://www.hashicorp.com/resources/everybody-talks-gossip-serf-memberlist-raft-swim-hashicorp-consul), [три](https://docs.datastax.com/en/cassandra-oss/3.x/cassandra/architecture/archGossipAbout.html), [четыре](https://hyperledger-fabric.readthedocs.io/en/latest/gossip.html), также см. шестой семинар), распространение блоков и транзакций в Bitcoin ([раз](https://nakamoto.com/bitcoins-p2p-network/), [два](https://arxiv.org/pdf/1703.08761.pdf), [три (видео)](https://www.dsn.kastel.kit.edu/bitcoin/videos.html)).
