// Ponte GDExtension do módulo `rogue` do ShatterCore (API C shatter_rogue_*, docs/tecnico/09 seção 16).
// Só repassa chamadas: nenhuma regra de jogo mora aqui. Saídas em JSON viram Dictionary/Array.
#pragma once

#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/string.hpp>

#include "shatter/shatter_c.h"

namespace godot {

class ShatterRogue : public RefCounted {
    GDCLASS(ShatterRogue, RefCounted)

public:
    ShatterRogue() = default;
    ~ShatterRogue() override;

    // Contexto e save. carregar_dados devolve "" se deu certo, ou a mensagem de erro.
    String carregar_dados(const String& pasta);
    void definir_save(const String& caminho);
    int meta_carregar();
    bool meta_salvar();
    String meta_texto_save() const;

    // Meta: os códigos são SHATTER_ROGUE_META_* (0 = ok).
    int meta_comprar(const String& id);
    int meta_pode_comprar(const String& id) const;
    int meta_criar(const String& id);
    int meta_pode_criar(const String& id) const;
    int meta_equipar(const String& id);
    void meta_preparar_corrida();
    int meta_creditar(const Dictionary& ganhos);
    Dictionary meta_estado() const;
    Dictionary drop_de(const String& inimigo) const;
    int habilidade_liberada(const String& upgrade) const;   // 1 liberada, 0 bloqueada, -1 desconhecida
    double configuracao(const String& chave) const;

    // Stats: objeto stat -> número.
    Dictionary aplicar_stats(const Dictionary& base, bool com_corrida) const;

    // Corrida.
    bool corrida_iniciar(int64_t semente, const Dictionary& base);
    int corrida_fase() const;
    Array corrida_caminhos(int etapa) const;
    Dictionary corrida_inimigo_morto(const String& inimigo);
    Dictionary corrida_escolher_carta(const String& upgrade, double hp);
    Dictionary corrida_descansar(double hp);
    int corrida_porta();
    int corrida_cartas_externas(bool ligado);   // só fora de corrida viva; 0 = ok
    int corrida_escolher_caminho(int indice);
    int corrida_jogador_morreu();
    int corrida_terminar();
    Dictionary corrida_estado() const;
    Dictionary corrida_stats() const;
    Dictionary corrida_resumo() const;

    // Habilidades por classe (API 1.10): os códigos são SHATTER_ROGUE_SKILL_* (0 = ok).
    int classe_definir(const String& classe);
    Dictionary habilidades_estado() const;
    Dictionary habilidade_def(const String& id, int nivel) const;   // nivel < 0 = atual; {} se desconhecida
    int habilidade_pode_aprender(const String& id) const;
    int habilidade_aprender(const String& id);
    int habilidade_equipar(int slot, const String& id);
    int habilidades_redistribuir();
    int habilidades_ganhar_pontos(int64_t pontos);
    void habilidades_tick(double dt);
    int habilidade_pode_usar(int slot, double mana) const;
    Dictionary habilidade_usar(int slot, double mana);              // {"resultado", "custo"}
    double habilidade_recarga(int slot) const;                      // 0..1
    Dictionary aplicar_passivas(const Dictionary& base) const;      // só as passivas da classe atual

    // Hordas (API 1.11, docs/09 seção 18): o core decide quem nasce e quando; os códigos são SHATTER_ROGUE_WAVE_*.
    int ondas_iniciar(const String& fase, int64_t semente);         // 0 = ok, 1 = fase desconhecida
    void ondas_parar();
    Array ondas_tick(double dt);                                     // passa dt e devolve os que nasceram agora
    Dictionary ondas_morto(int64_t id);                              // {"resultado", "completa"}
    int ondas_acordar_chefe();                                       // 0 = acordou (ver SHATTER_ROGUE_WAVE_*)
    Dictionary ondas_estado() const;
    Dictionary ondas_definicoes() const;
    String ondas_estado_texto() const;
    bool ondas_restaurar(const String& texto);
    String ondas_hash() const;

    // XP, nível, baú, curva, vida do chefe e modo horda (API 1.12, docs/09 seção 19). Códigos: SHATTER_ROGUE_RUN_*.
    int horda_definir(bool ligado);
    int horda_vencer();
    Dictionary nivel_xp_da_morte(const String& inimigo, double xp_mult, bool elite) const;  // {"resultado","xp","bau"}
    Dictionary nivel_ganhar_xp(int64_t xp);                         // {"resultado", "niveis"}
    int nivel_abrir_bau();
    Dictionary nivel_escolher(const String& upgrade, double hp);    // {"resultado", "hp"}
    int nivel_sortear_de_novo();
    int nivel_pular();
    int nivel_banir(const String& upgrade);
    Dictionary nivel_estado() const;
    Dictionary curva(const String& fase, int onda) const;           // {"hp","damage","speed","xp"}
    double vida_chefe(double base, double dps) const;

    // Estado completo e determinismo.
    String estado_texto() const;
    bool estado_restaurar(const String& texto);
    String estado_hash() const;

protected:
    static void _bind_methods();

private:
    shatter_rogue* rogue_ = nullptr;
    String save_path_;
};

}  // namespace godot
