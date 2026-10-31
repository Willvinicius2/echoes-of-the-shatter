// ShatterCore — árvore de habilidades por classe do roguelike 2D (rogue.h, API 1.10; docs/tecnico/09 seção 17).
// Paridade com godot/scripts2d/habilidades_2d.gd: pontos, pré-requisito pelo pai, níveis, 4 slots, redistribuição,
// passivas sobre os stats, definição escalonada pelo nível e recargas. Mana e efeitos ficam no cliente.
#include <algorithm>
#include <cmath>
#include <limits>

#include "shatter/rogue.h"

namespace shatter {

namespace {

// Campos que crescem com o nível (CAMPOS_ESCALA do habilidades_2d.gd). cd e custo não escalam.
constexpr const char* kScaledColumns[] = {"dano", "qtd", "raio", "duracao", "alcance", "valor"};
// Stat que multiplica a recarga das habilidades (contrato com player.csv, como hp_max).
constexpr std::string_view kSkillCdMultStat = "skill_cd_mult";

bool IsScaled(const std::string& col) {
    for (const char* c : kScaledColumns)
        if (col == c) return true;
    return false;
}

bool ValidSlot(int slot) { return slot >= 0 && slot < kRogueSkillSlots; }

}  // namespace

void RogueState::ResetSkillState() {
    skillMeta_.clear();
    class_ = -1;
    if (data_ == nullptr) return;
    const auto& classes = data_->Classes();
    skillMeta_.resize(classes.size());
    for (std::size_t c = 0; c < classes.size(); ++c) skillMeta_[c].levels.assign(classes[c].skills.size(), 0);
    if (!classes.empty()) class_ = 0;  // classe padrão: a 1ª de classes_2d.csv (meta.classe = "arqueiro" no GDScript)
    ClearCooldowns();
}

void RogueState::ClearCooldowns() {
    cooldowns_.clear();
    if (data_ != nullptr && class_ >= 0)
        cooldowns_.assign(data_->Classes()[static_cast<std::size_t>(class_)].skills.size(), 0.0);
}

const ContentId& RogueState::ClassId() const {
    static const ContentId kNone;
    if (data_ == nullptr || class_ < 0) return kNone;
    return data_->Classes()[static_cast<std::size_t>(class_)].id;
}

RogueSkillResult RogueState::SetClass(std::string_view classId) {
    const int c = data_ != nullptr ? data_->FindClass(classId) : -1;
    if (c < 0) return RogueSkillResult::Unknown;
    if (phase_ != RoguePhase::None && phase_ != RoguePhase::Won && phase_ != RoguePhase::Dead)
        return RogueSkillResult::WrongPhase;
    class_ = c;
    ClearCooldowns();
    return RogueSkillResult::Ok;
}

std::int64_t RogueState::SkillPoints() const {
    return class_ >= 0 ? skillMeta_[static_cast<std::size_t>(class_)].points : 0;
}

int RogueState::SkillLevel(std::string_view skillId) const {
    const int i = data_ != nullptr ? data_->FindSkill(class_, skillId) : -1;
    return i < 0 ? 0 : skillMeta_[static_cast<std::size_t>(class_)].levels[static_cast<std::size_t>(i)];
}

const ContentId& RogueState::SkillSlot(int slot) const {
    static const ContentId kNone;
    if (data_ == nullptr || class_ < 0 || !ValidSlot(slot)) return kNone;
    const int i = skillMeta_[static_cast<std::size_t>(class_)].slots[static_cast<std::size_t>(slot)];
    return i < 0 ? kNone : data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)].id;
}

RogueSkillResult RogueState::CheckLearn(std::string_view skillId) const {
    if (data_ == nullptr || class_ < 0) return RogueSkillResult::NoClass;
    const int i = data_->FindSkill(class_, skillId);
    if (i < 0) return RogueSkillResult::Unknown;
    const RogueSkillMeta& m = skillMeta_[static_cast<std::size_t>(class_)];
    const RogueSkillDef& d = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)];
    if (m.levels[static_cast<std::size_t>(i)] >= d.maxLevel) return RogueSkillResult::Maxed;
    if (m.points < d.points) return RogueSkillResult::NoPoints;
    if (d.parentIndex >= 0 && m.levels[static_cast<std::size_t>(d.parentIndex)] < 1) return RogueSkillResult::Locked;
    return RogueSkillResult::Ok;
}

RogueSkillResult RogueState::Learn(std::string_view skillId) {
    const RogueSkillResult r = CheckLearn(skillId);
    if (r != RogueSkillResult::Ok) return r;
    const int i = data_->FindSkill(class_, skillId);
    RogueSkillMeta& m = skillMeta_[static_cast<std::size_t>(class_)];
    const RogueSkillDef& d = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)];
    m.points -= d.points;
    const int lv = ++m.levels[static_cast<std::size_t>(i)];
    if (lv == 1 && d.active && std::find(m.slots.begin(), m.slots.end(), i) == m.slots.end()) {
        for (int& s : m.slots) {
            if (s < 0) {
                s = i;
                break;
            }
        }
    }
    return r;
}

RogueSkillResult RogueState::AddSkillPoints(std::int64_t n) {
    if (data_ == nullptr || class_ < 0) return RogueSkillResult::NoClass;
    if (n <= 0) return RogueSkillResult::Ok;
    RogueSkillMeta& m = skillMeta_[static_cast<std::size_t>(class_)];
    const std::int64_t cap = std::numeric_limits<std::int64_t>::max();
    m.points = m.points > cap - n ? cap : m.points + n;
    return RogueSkillResult::Ok;
}

RogueSkillResult RogueState::Respec() {
    if (data_ == nullptr || class_ < 0) return RogueSkillResult::NoClass;
    RogueSkillMeta& m = skillMeta_[static_cast<std::size_t>(class_)];
    const auto& skills = data_->Classes()[static_cast<std::size_t>(class_)].skills;
    const std::int64_t cap = std::numeric_limits<std::int64_t>::max();
    for (std::size_t i = 0; i < m.levels.size(); ++i) {
        const std::int64_t refund = static_cast<std::int64_t>(skills[i].points) * m.levels[i];
        m.points = m.points > cap - refund ? cap : m.points + refund;
        m.levels[i] = 0;
    }
    m.slots.fill(-1);
    return RogueSkillResult::Ok;
}

RogueSkillResult RogueState::EquipSkill(int slot, std::string_view skillId) {
    if (data_ == nullptr || class_ < 0) return RogueSkillResult::NoClass;
    if (!ValidSlot(slot)) return RogueSkillResult::BadSlot;
    RogueSkillMeta& m = skillMeta_[static_cast<std::size_t>(class_)];
    const std::size_t k = static_cast<std::size_t>(slot);
    if (skillId.empty()) {
        m.slots[k] = -1;
        return RogueSkillResult::Ok;
    }
    const int i = data_->FindSkill(class_, skillId);
    if (i < 0) return RogueSkillResult::Unknown;
    if (!data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)].active)
        return RogueSkillResult::NotActive;
    if (m.levels[static_cast<std::size_t>(i)] < 1) return RogueSkillResult::NotLearned;
    for (int& s : m.slots)
        if (s == i) s = m.slots[k];  // estava em outro slot: os dois trocam
    m.slots[k] = i;
    return RogueSkillResult::Ok;
}

bool RogueState::SkillDefAt(std::string_view skillId, int level, RogueSkillLevelDef& out) const {
    out = RogueSkillLevelDef();
    const int i = data_ != nullptr ? data_->FindSkill(class_, skillId) : -1;
    if (i < 0) return false;
    const RogueSkillDef& d = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)];
    const int lv = level < 0 ? skillMeta_[static_cast<std::size_t>(class_)].levels[static_cast<std::size_t>(i)] : level;
    const double f = 1.0 + d.scale * std::max(0.0, static_cast<double>(lv) - 1.0);
    out.level = lv;
    out.texts = d.texts;
    out.numbers = d.numbers;
    for (auto& p : out.numbers) {
        if (!IsScaled(p.first)) continue;
        p.second *= f;
        if (p.first == "qtd") p.second = p.second > 0.0 ? std::max(1.0, std::round(p.second)) : 0.0;
    }
    return true;
}

RogueStats RogueState::ApplySkillPassives(const RogueStats& stats) const {
    RogueStats s = stats;
    if (data_ == nullptr || class_ < 0) return s;
    const auto& skills = data_->Classes()[static_cast<std::size_t>(class_)].skills;
    const auto& levels = skillMeta_[static_cast<std::size_t>(class_)].levels;
    for (std::size_t i = 0; i < skills.size(); ++i) {
        const RogueSkillDef& d = skills[i];
        if (d.active || d.stat.empty() || levels[i] <= 0) continue;
        auto it = std::find_if(s.begin(), s.end(), [&](const auto& p) { return p.first == d.stat; });
        if (it == s.end()) {
            s.emplace_back(d.stat, 0.0);
            it = s.end() - 1;
        }
        for (int n = 0; n < levels[i]; ++n)
            it->second = d.mode == RogueMode::Mult ? it->second * (1.0 + d.value) : it->second + d.value;
    }
    return s;
}

void RogueState::TickSkills(double dt) {
    if (!(dt > 0.0) || !(dt < 1e12)) return;
    for (double& c : cooldowns_) c = c > dt ? c - dt : 0.0;
}

double RogueState::SkillCooldownLeft(std::string_view skillId) const {
    const int i = data_ != nullptr ? data_->FindSkill(class_, skillId) : -1;
    return i < 0 ? 0.0 : cooldowns_[static_cast<std::size_t>(i)];
}

double RogueState::SlotCooldownFraction(int slot) const {
    if (data_ == nullptr || class_ < 0 || !ValidSlot(slot)) return 0.0;
    const int i = skillMeta_[static_cast<std::size_t>(class_)].slots[static_cast<std::size_t>(slot)];
    if (i < 0) return 0.0;
    const double left = cooldowns_[static_cast<std::size_t>(i)];
    if (left <= 0.0) return 0.0;
    const double cd = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)].cooldown;
    return std::clamp(left / std::max(0.01, cd), 0.0, 1.0);
}

RogueSkillResult RogueState::CheckUse(int slot, double mana) const {
    if (data_ == nullptr || class_ < 0) return RogueSkillResult::NoClass;
    if (!ValidSlot(slot)) return RogueSkillResult::BadSlot;
    const int i = skillMeta_[static_cast<std::size_t>(class_)].slots[static_cast<std::size_t>(slot)];
    if (i < 0) return RogueSkillResult::EmptySlot;
    if (cooldowns_[static_cast<std::size_t>(i)] > 0.0) return RogueSkillResult::Cooldown;
    const double cost = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)].cost;
    if (!(mana >= cost)) return RogueSkillResult::NoMana;
    return RogueSkillResult::Ok;
}

RogueSkillResult RogueState::CommitUse(int slot, double mana, double* costOut) {
    if (costOut != nullptr) *costOut = 0.0;
    const RogueSkillResult r = CheckUse(slot, mana);
    if (r != RogueSkillResult::Ok) return r;
    const int i = skillMeta_[static_cast<std::size_t>(class_)].slots[static_cast<std::size_t>(slot)];
    const RogueSkillDef& d = data_->Classes()[static_cast<std::size_t>(class_)].skills[static_cast<std::size_t>(i)];
    double mult = 1.0;
    if (phase_ != RoguePhase::None) {
        for (const auto& p : RunStats())
            if (p.first == kSkillCdMultStat) mult = p.second;
    }
    if (d.cooldown > 0.0) cooldowns_[static_cast<std::size_t>(i)] = std::max(0.0, d.cooldown * mult);
    if (costOut != nullptr) *costOut = d.cost;
    return r;
}

}  // namespace shatter
