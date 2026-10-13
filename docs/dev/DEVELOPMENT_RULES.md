# Development Rules - Anti-Overwrite Principles

## Core Principle: Immutable Data Flow

> **لا تعدّل الأصل — أنشئ نسخة — استخدم متغيرات جديدة — افصل بين input و output — فكر "immutable"**

---

## Rules for Preventing Overwrite Bugs

### 1. Never Mutate Input Data
```python
# ❌ BAD - Mutates original
def process(data):
    data["new_field"] = "value"
    return data

# ✅ GOOD - Creates new object
def process(data):
    return {**data, "new_field": "value"}
```

### 2. Separate Input/Output Variables
```python
# ❌ BAD - Reuses variable
coords = get_coords()
coords = transform(coords)  # Original lost!

# ✅ GOOD - Distinct names
raw_coords = get_coords()
transformed_coords = transform(raw_coords)
```

### 3. Use Immutable Patterns for Settings
```python
# ❌ BAD - Direct mutation
settings["latitude"] = new_lat

# ✅ GOOD - Copy then modify
new_settings = {**settings, "latitude": new_lat, "custom_coords": True}
```

### 4. Protect Critical State with Flags
```python
# Coordinate protection pattern
if key in ("latitude", "longitude"):
    new_settings = {**settings, key: value, "custom_coords": True}
```

### 5. Factory Functions for Complex Objects
```python
# ✅ GOOD - Returns new instance
def create_prayer_result(base, overrides):
    return PrayerTimesResult(
        fajr=overrides.get("fajr", base.fajr),
        sunrise=overrides.get("sunrise", base.sunrise),
        # ...
    )
```

### 6. QML: Use Properties, Not Direct Mutation
```qml
// ❌ BAD
textField.onTextChanged: settings.latitude = text

// ✅ GOOD
TextField {
    onTextChanged: backendController.updateSetting("latitude", parseFloat(text))
}
```

---

## Coordinate Protection Implementation

The `custom_coords` flag pattern prevents overwrites:

```python
# In updateSetting():
if key in ("latitude", "longitude"):
    self._settings[key] = value
    self._settings["custom_coords"] = True  # PROTECTION FLAG

# In resetToAutoCoordinates():
if not self._settings.get("custom_coords", False):
    # Safe to auto-update
    self._settings["latitude"] = auto_lat
    self._settings["longitude"] = auto_lon
```

---

## Benefits

| Problem | Solution |
|---------|----------|
| Country change overwrites manual coords | `custom_coords` flag blocks auto-update |
| Settings mutation across components | Immutable updates via `updateSetting()` |
| Lost original values | Separate input/output variables |
| Debugging difficulty | Clear data flow: input → transform → output |

---

## Enforcement

- **Code Review**: Check for direct dict/list mutations
- **Static Analysis**: Flag `dict.update()`, `list.append()` on shared state
- **Tests**: Verify `resetToAutoCoordinates()` restores correctly
- **Documentation**: This file as reference
