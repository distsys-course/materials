# Полезные материалы 

## DNS

- [Интерактивный гайд как работает DNS](https://howdns.works/)
- [Список Top Level Domain](https://data.iana.org/TLD/tlds-alpha-by-domain.txt)
- [Онлайн утилита от Google для анализа DNS записей](https://dns.google/)
- [Типы DNS серверов (Recursive, Authoritative)](https://www.cloudflare.com/learning/dns/dns-server-types/)
- [Интерактивная карта с Root серверами](https://root-servers.org/)
- [Предназначение различных типов DNS записей](https://en.wikipedia.org/wiki/List_of_DNS_record_types)
- [Информация про etc/resolv.conf](https://man7.org/linux/man-pages/man5/resolv.conf.5.html)
- Популярные публичные DNS сервера, если DSN вашего ISP работает плохо: 1.1.1.1 (CloudFlare), 8.8.8.8 (Google)
- [Dropbox про скорость распространения DNS и влияние TTL (глава GeoDNS)](https://dropbox.tech/infrastructure/dropbox-traffic-infrastructure-edge-network)
- Бонус про безопасность: [DNS Spoofing](https://www.cloudflare.com/learning/dns/dns-cache-poisoning/) и [DNSSEC](https://www.icann.org/resources/pages/dnssec-what-is-it-why-important-2019-03-05-en)

Также будет полезно научиться пользоваться утилитой dig (практический гайд [тут](https://metebalci.com/blog/a-short-practical-tutorial-of-dig-dns-and-dnssec/)):
```bash
# Получить IP домена
dig wikipedia.org

# Если вам нужна не A запись, а какая-то другая, можно это явно указать
dig wikipedia.org NS

# Получить домен по IP
dig -x 185.15.59.224

# Флаг +trace позволяет отследить путь resolve запроса: root servers -> tld server -> authoritative dns server
dig +trace wikipedia.org

# Получить список root серверов
dig . NS

# Обратиться к определенному DNS серверу (g.root-servers.net) и узнать у него информацию по NS записям для org.
dig @g.root-servers.net org. NS

# Обратиться к DNS серверу 199.19.57.1 и узнать список authoritative серверов для wikipedia.org
dig @199.19.57.1 wikipedia.org NS

# Узнать у authoritative сервера IP адрес wikipedia.org
dig @ns0.wikimedia.org. wikipedia.org A

# Сделать запрос curl'ом по IP, подставив Host
curl https://185.15.58.224 -k -H 'Host: www.wikipedia.org' -v

# Authoritative сервер может отдавать разные IP адреса в зависимости от расположения сервера, запрашивающего информацию
# Обычно это используют для маршрутизации трафика к ближайшей зоне доступности, где есть сервера (GeoDNS)
dig @8.8.8.8 www.wikipedia.org. A
dig @77.88.8.8  www.wikipedia.org. A
```

## Extra

- [Что происходит, когда вы вбиваете URL в адресную строку браузера](https://aws.amazon.com/blogs/mobile/what-happens-when-you-type-a-url-into-your-browser/)
- [Базовый дизайн BitTorrent и других p2p-сетей](https://web.cs.ucla.edu/classes/cs217/05BitTorrent.pdf#page9)
