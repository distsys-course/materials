# Рассылка в группе (multicast)

## План Глеба

1. Какие паттерны коммуникцаии мы уже обсуждали? client-server, server-server
2. Если я хочу отправить какое-то сообщение всему кластеру, что делать? unicast (квадрат сообщений), gossip
3. Давайте сообразим как делать service discovery: с мастером, с распределенным мастером, без мастера
4. Концептуально про IP Multicast и что его практически никто не использует, хотя идея забавная, можно про no-server DNS задачку предложить
5. Немного про твитч — как от N стримеров поток попадает к тысячам клиентов, откуда появляются задержки
6. WebSocket, отличия от голого TCP и задача бродкаста сообщений клиентам, какому-то ограниченному их списку (например, если ключ сокета это clientId, userId, бродкастер шардирован по clientId, а хочется отправить конкретному пользователю)
7. Разбор вопросов по ДЗ

## План Олега

- Разобрать примеры программ, использующих IP Multicast:
  - [https://pymotw.com/3/socket/multicast.html](https://pymotw.com/3/socket/multicast.html)
  - также можно рассказать как устроены IP-адреса мультикаст групп, как понять какие адреса зарезервированы и кем...
  - повторить какие гарантии дает мультикаст поверх UDP
- Поговорить о применении IP Multicast в жизни:
  - zeroconf, DNS без сервера, обнаружение узлов в кластере...
  - [https://en.wikipedia.org/wiki/Zero-configuration_networking](https://en.wikipedia.org/wiki/Zero-configuration_networking)
  - [https://en.wikipedia.org/wiki/Multicast_DNS](https://en.wikipedia.org/wiki/Multicast_DNS)
  - [https://www.oreilly.com/library/view/cisco-ios-cookbook/0596527225/ch14s11.html](https://www.oreilly.com/library/view/cisco-ios-cookbook/0596527225/ch14s11.html)
  - [https://ignite.apache.org/docs/latest/clustering/tcp-ip-discovery](https://ignite.apache.org/docs/latest/clustering/tcp-ip-discovery)
  - есть ли успешные примеры за пределами локальной сети?
- Gossip и его применения:
  - Наглядный симулятор для понимания принципов: [https://flopezluis.github.io/gossip-simulator/](https://flopezluis.github.io/gossip-simulator/)
  - Использование gossip для рассылки и membership в продуктах HashiCorp:
      - [https://www.consul.io/docs/architecture/gossip](https://www.consul.io/docs/architecture/gossip)
      - [https://www.serf.io/docs/internals/gossip.html](https://www.serf.io/docs/internals/gossip.html)
      - [https://www.hashicorp.com/resources/everybody-talks-gossip-serf-memberlist-raft-swim-hashicorp-consul](https://www.hashicorp.com/resources/everybody-talks-gossip-serf-memberlist-raft-swim-hashicorp-consul)
  - Cassandra: [https://docs.datastax.com/en/cassandra-oss/3.x/cassandra/architecture/archGossipAbout.html](https://docs.datastax.com/en/cassandra-oss/3.x/cassandra/architecture/archGossipAbout.html)
  - Amazon S3 uses a gossip protocol to quickly spread server state information throughout the system: [https://status.aws.amazon.com/s3-20080720.html](https://status.aws.amazon.com/s3-20080720.html)
- Разбор статьи про Plumtree унести в НИС