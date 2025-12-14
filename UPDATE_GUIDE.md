## 🆕 Nové funkce v nejnovější verzi

### ⏰ Denní načítání dat
- **Změna**: Data z ČEZ distribuce se nyní načítají **jednou denně v 01:00** místo každou hodinu
- **Výhody**: 
  - Snížení zátěže API serveru
  - Stabilnější provoz
  - Menší spotřeba síťových prostředků

### 🕐 Dynamické zobrazení zbývajícího času
- **Nové entity** se aktualizují **každou sekundu** a zobrazují přesný zbývající čas
- **Žádné další API volání** - výpočty jsou založené na denně načtených datech

### 📊 Nové senzory

| Entity | Popis | Aktualizace |
|--------|-------|-------------|
| `sensor.cez_hdo_lowtariffremaining` | Zbývající čas současné nízké tarify | Každou sekundu |
| `sensor.cez_hdo_hightariffremaining` | Zbývající čas současné vysoké tarify | Každou sekundu |
| `sensor.cez_hdo_nextlowtariffcountdown` | Odpočet do začátku příští nízké tarify | Každou sekundu |
| `sensor.cez_hdo_nexthightariffcountdown` | Odpočet do začátku příští vysoké tarify | Každou sekundu |

### 🎯 Atributy nových senzorů

Každý z nových "zbývající čas" senzorů obsahuje:
- **`state`**: Počet zbývajících sekund (číslo)
- **`formatted_time`**: Čas ve formátu `HH:MM:SS` 
- **`display_text`**: Lidsky čitelný text (např. "Zbývá 02:15:30" nebo "Za 05:45:12")

### 💡 Příklad použití v lovelace kartě

```yaml
type: entities
entities:
  - entity: binary_sensor.cez_hdo_lowtariffactive
    name: "Nízká tarifa aktivní"
  - entity: sensor.cez_hdo_lowtariffremaining
    name: "Zbývající čas nízké tarify"
    attribute: display_text
  - entity: sensor.cez_hdo_nextlowtariffcountdown  
    name: "Příští nízká tarifa za"
    attribute: display_text
```

### 🔄 Migrace z předchozí verze

**Žádné změny v konfiguraci nejsou potřeba!** 

Vaše stávající konfigurace zůstává stejná:
```yaml
sensor:
  - platform: cez_hdo
    ean: "VAŠE_EAN_ČÍSLO"
    
binary_sensor:
  - platform: cez_hdo
    ean: "VAŠE_EAN_ČÍSLO"
```

Nové entity se vytvoří automaticky při restartu Home Assistant.