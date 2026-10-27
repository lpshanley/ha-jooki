# Changelog

## [0.1.1](https://github.com/lpshanley/ha-jooki/compare/0.1.0...0.1.1) (2026-10-27)


### Bug Fixes

* **jooki:** stop polling push entities ([1a4ae48](https://github.com/lpshanley/ha-jooki/commit/1a4ae48ebb23363f6734dcdf409380468418721a))
* **manifest:** allow Home Assistant to own paho-mqtt ([f7bdf9d](https://github.com/lpshanley/ha-jooki/commit/f7bdf9dbe7f74ae85d1c5c5588868b273adf2570))
* **manifest:** drop categories until hassfest accepts them ([cdfa54a](https://github.com/lpshanley/ha-jooki/commit/cdfa54a74ed14f3aa3288b022aa4919424bc3964))
* **media-player:** play a figurine by tag or star ([0fda4ed](https://github.com/lpshanley/ha-jooki/commit/0fda4ed81e9aef4bffaf8ea2110cbe9747292587))
* **models:** keep commanded Toy Safe when a later slice omits it ([8df64ab](https://github.com/lpshanley/ha-jooki/commit/8df64ab18e82b6d8462a9e698e29196e3bc8168c))
* **models:** replace partial MQTT state by slice ([44463c4](https://github.com/lpshanley/ha-jooki/commit/44463c4caa6aa57c7e3fd3a63c46d2faa36b3e1a))
* **mqtt:** apply local audio events inside accumulated state ([701123f](https://github.com/lpshanley/ha-jooki/commit/701123f491df207771499f63069a7a86706a0952))
* **mqtt:** track the J2000 headphone jack ([dcdcaa3](https://github.com/lpshanley/ha-jooki/commit/dcdcaa3a8227ed3e684434129e269d8abfbf20e7))
* **select:** keep the chosen language across state slices ([15c1f80](https://github.com/lpshanley/ha-jooki/commit/15c1f80ed7d90c01039e5395ce0e6c03a3486ad2))
* **switch:** record Toy Safe on the device state ([2744c43](https://github.com/lpshanley/ha-jooki/commit/2744c435d56009bd9e73a519d08ca6228ac4611c))


### Performance

* **models:** rebuild only the state slice that arrived ([76e3964](https://github.com/lpshanley/ha-jooki/commit/76e3964e97bd5f02f4c0d281a8ff2df816f8abd2))
* **mqtt:** enqueue publishes on the client thread ([e433feb](https://github.com/lpshanley/ha-jooki/commit/e433febf6159eba35f610fea1734ecab7f7c1d4b))
* **mqtt:** handle messages on the event loop ([1daa1ce](https://github.com/lpshanley/ha-jooki/commit/1daa1cee874d21071e351c227c79a67bbbcfa61c))


### Maintenance

* **config-flow:** drop an unused device version import ([6bbe412](https://github.com/lpshanley/ha-jooki/commit/6bbe412ce14bdc146b0e3d3a79ed9f42fb31e6af))
* **jooki:** declare the device operation surface ([c1eba65](https://github.com/lpshanley/ha-jooki/commit/c1eba656bfa06f0be5bc0dd43d0abc60448effa0))
* **jooki:** encode NFC, LED, locale, and skip commands ([c0fe810](https://github.com/lpshanley/ha-jooki/commit/c0fe810ee29c423cb5a6d194831369f13e93b93c))
* **jooki:** encode playback commands outside the client ([823d152](https://github.com/lpshanley/ha-jooki/commit/823d152571d6cc2b806b9d5493aa3289b901a48f))
* **jooki:** move topic maps into device_config ([97070b0](https://github.com/lpshanley/ha-jooki/commit/97070b0c61ab5e363848b8b09b9af7e260fc651c))
* **jooki:** platforms call the device instead of MQTT topics ([f0ce1af](https://github.com/lpshanley/ha-jooki/commit/f0ce1af925378b84229d5e328d1a857994bf1d8a))
* **mqtt:** import device config from its module ([ff3b878](https://github.com/lpshanley/ha-jooki/commit/ff3b878fd41b9eb3ee14b030be7636b3a52f418e))
* **mqtt:** send commands through the payload encoders ([562571a](https://github.com/lpshanley/ha-jooki/commit/562571a0207e5141403d4e3547c1ce9f2eb37326))
