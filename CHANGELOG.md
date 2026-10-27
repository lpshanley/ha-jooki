# Changelog

## [0.4.0](https://github.com/lpshanley/ha-jooki/compare/0.3.0...0.4.0) (2026-10-27)


### Features

* **discovery:** confirm a DHCP player with ping and MQTT ([efd613a](https://github.com/lpshanley/ha-jooki/commit/efd613a9f9ceb297ef00225878e2435d109fe09e))
* **discovery:** latch the player hostname as the unique id ([8f05492](https://github.com/lpshanley/ha-jooki/commit/8f054920cade38eb9530035a450e16d2e9f18372))
* **identity:** recognize a Jooki hostname ([a435b2b](https://github.com/lpshanley/ha-jooki/commit/a435b2bac7ba819995ab625a797f2a7bd9701598))

## [0.3.0](https://github.com/lpshanley/ha-jooki/compare/0.2.0...0.3.0) (2026-10-27)


### ⚠ BREAKING CHANGES

* **figurine:** The Figurine sensor state is no longer always the star id. Automations that matched it to a star id such as Jooki.Dragon must use the star_id field on figurine_placed when a token name or bound playlist title exists. star_id stays on the event, and the NFC Tag ID sensor is unchanged.

### Features

* **bluetooth:** expose the connected speaker ([bb65b3c](https://github.com/lpshanley/ha-jooki/commit/bb65b3ce83bdff380d3b0153dbfd3df0fd404cdb))
* **deezer:** expose the connected account ([3ef01aa](https://github.com/lpshanley/ha-jooki/commit/3ef01aaa385cd33cda6b1fc02661dda71adafcd0))
* **figurine:** show the parent-facing figurine name ([3c82651](https://github.com/lpshanley/ha-jooki/commit/3c826519319462eefcab07cec708d3d644892fe2))
* **messages:** dismiss a device message by id ([2eb216c](https://github.com/lpshanley/ha-jooki/commit/2eb216c5ab3086a4d89af3db604bd4cfea3f4f61))
* **messages:** parse device messages from their own slice ([12d1acd](https://github.com/lpshanley/ha-jooki/commit/12d1acd405688243a5e76eb52423e7b587e368de))
* **messages:** show the newest device message ([cb350df](https://github.com/lpshanley/ha-jooki/commit/cb350dfda95954d060b761aa283de1b9dbe25adf))
* **playback:** expose the explicit-track flag ([62d63c9](https://github.com/lpshanley/ha-jooki/commit/62d63c98b21fb344928599a27f7b63f99eefd116))
* **power:** expose battery temperature in celsius ([d6c0f66](https://github.com/lpshanley/ha-jooki/commit/d6c0f661ec4778b99c8579c77f3f9c736f9cb982))


### Maintenance

* **services:** share device lookup for service calls ([84de839](https://github.com/lpshanley/ha-jooki/commit/84de839dcf4407b79b1f239d8777eb30574a2be3))


### Miscellaneous

* set the next release to 0.2.1 ([4f55829](https://github.com/lpshanley/ha-jooki/commit/4f55829099032ded754ff581fcc8b54c67bbf7f4))
* set the next release to 0.3.0 ([0d56c98](https://github.com/lpshanley/ha-jooki/commit/0d56c9882f8a52431c6e13948c5ef813293cb82a))
