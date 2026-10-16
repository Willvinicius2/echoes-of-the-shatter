// ShatterCore — conversões texto <-> enum de types.h e item.h.
#include "shatter/item.h"
#include "shatter/types.h"

namespace shatter {

namespace {

struct TagName {
    const char* name;
    Tag tag;
};
constexpr TagName kTagNames[kTagCount] = {
    {"attack", Tag::Attack},       {"spell", Tag::Spell},         {"melee", Tag::Melee},
    {"projectile", Tag::Projectile}, {"area", Tag::Area},         {"fire", Tag::Fire},
    {"cold", Tag::Cold},           {"lightning", Tag::Lightning}, {"physical", Tag::Physical},
};

constexpr const char* kSlotNames[kItemSlotCount] = {
    "main_hand", "off_hand", "head", "body", "hands", "feet", "amulet", "ring", "ring2", "belt",
};

}  // namespace

// Aceita '|' (CSV) e '+' (dentro de modificadores) como separador. Texto vazio = nenhuma tag.
bool ParseTagList(std::string_view text, TagMask& out) {
    TagMask mask = 0;
    if (!text.empty()) {
        std::size_t pos = 0;
        while (true) {
            std::size_t next = text.find_first_of("|+", pos);
            const std::string_view item =
                text.substr(pos, next == std::string_view::npos ? std::string_view::npos : next - pos);
            bool found = false;
            for (const TagName& t : kTagNames) {
                if (item == t.name) {
                    mask |= Mask(t.tag);
                    found = true;
                    break;
                }
            }
            if (!found) return false;
            if (next == std::string_view::npos) break;
            pos = next + 1;
        }
    }
    out = mask;
    return true;
}

std::string TagListToString(TagMask mask) {
    std::string s;
    for (const TagName& t : kTagNames) {
        if ((mask & Mask(t.tag)) != 0) {
            if (!s.empty()) s += '|';
            s += t.name;
        }
    }
    return s;
}

bool ParseDamageType(std::string_view text, DamageType& out) {
    if (text == "physical") { out = DamageType::Physical; return true; }
    if (text == "fire") { out = DamageType::Fire; return true; }
    if (text == "cold") { out = DamageType::Cold; return true; }
    if (text == "lightning") { out = DamageType::Lightning; return true; }
    return false;
}

const char* ToString(DamageType t) {
    switch (t) {
        case DamageType::Physical: return "physical";
        case DamageType::Fire: return "fire";
        case DamageType::Cold: return "cold";
        case DamageType::Lightning: return "lightning";
    }
    return "physical";
}

bool ParseRarity(std::string_view text, Rarity& out) {
    if (text == "normal") { out = Rarity::Normal; return true; }
    if (text == "magic") { out = Rarity::Magic; return true; }
    if (text == "rare") { out = Rarity::Rare; return true; }
    if (text == "unique") { out = Rarity::Unique; return true; }
    return false;
}

const char* ToString(Rarity r) {
    switch (r) {
        case Rarity::Normal: return "normal";
        case Rarity::Magic: return "magic";
        case Rarity::Rare: return "rare";
        case Rarity::Unique: return "unique";
    }
    return "normal";
}

bool ParseItemSlot(std::string_view text, ItemSlot& out) {
    for (int i = 0; i < kItemSlotCount; ++i) {
        if (text == kSlotNames[i]) {
            out = static_cast<ItemSlot>(i);
            return true;
        }
    }
    return false;
}

const char* ToString(ItemSlot s) {
    const int i = static_cast<int>(s);
    return (i >= 0 && i < kItemSlotCount) ? kSlotNames[i] : "main_hand";
}

}  // namespace shatter
