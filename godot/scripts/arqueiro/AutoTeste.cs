using Godot;

namespace EchoesOfTheShatter.Arqueiro;

/// <summary>
/// Teste automático (rodar com: -- --arqueiro-teste). Injeta eventos reais de entrada (mouse e gamepad pelo Input.ParseInputEvent),
/// confere a mira contra um cálculo independente (câmera pinhole x plano do chão), tira capturas e imprime linhas TESTE:.
/// Para outra resolução: Godot ... --resolution 1280x720 -- --arqueiro-teste
/// </summary>
public partial class AutoTeste : Node
{
    ArqueiroController _h;
    CameraArqueiro _cam;
    string _dir;
    PackedScene _cenaDummy;

    async System.Threading.Tasks.Task Espera(float s)
        => await ToSignal(GetTree().CreateTimer(s, true, false, true), SceneTreeTimer.SignalName.Timeout);

    async System.Threading.Tasks.Task Fisica(int n = 1)
    {
        for (int i = 0; i < n; i++) await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
    }

    void Foto(string nome)
    {
        GetViewport().GetTexture().GetImage().SavePng(_dir + nome + ".png");
        GD.Print("TESTE: captura " + nome);
    }

    void Recorte(string nome, Vector3 mundo, int meio = 110)
    {
        var img = GetViewport().GetTexture().GetImage();
        var p = _cam.UnprojectPosition(mundo);
        int x = Mathf.Clamp((int)p.X - meio, 0, img.GetWidth() - 2 * meio), y = Mathf.Clamp((int)p.Y - meio, 0, img.GetHeight() - 2 * meio);
        var c = img.GetRegion(new Rect2I(x, y, 2 * meio, 2 * meio));
        c.Resize(2 * meio * 3, 2 * meio * 3, Image.Interpolation.Nearest);
        c.SavePng(_dir + nome + ".png");
        GD.Print($"TESTE: recorte {nome} tela=({p.X:0},{p.Y:0})");
    }

    // ---------- entrada injetada
    void Mouse(Vector2 px)
        => Input.ParseInputEvent(new InputEventMouseMotion { Position = px, GlobalPosition = px });

    void Clique(Vector2 px, bool baixo)
        => Input.ParseInputEvent(new InputEventMouseButton { ButtonIndex = MouseButton.Left, Pressed = baixo, Position = px, GlobalPosition = px, ButtonMask = baixo ? MouseButtonMask.Left : 0 });

    void Eixo(JoyAxis a, float v) => Input.ParseInputEvent(new InputEventJoypadMotion { Axis = a, AxisValue = v });
    void Botao(JoyButton b, bool baixo) => Input.ParseInputEvent(new InputEventJoypadButton { ButtonIndex = b, Pressed = baixo });

    /// <summary>Ponto do chão (plano y) sob o pixel, calculado à mão (pinhole), sem usar ProjectRay*.</summary>
    Vector3 PontoIndep(Vector2 px, float y)
    {
        var tam = GetViewport().GetVisibleRect().Size;
        float t = Mathf.Tan(Mathf.DegToRad(_cam.Fov) / 2f);
        var dc = new Vector3((px.X / tam.X * 2f - 1f) * (tam.X / tam.Y) * t, (1f - px.Y / tam.Y * 2f) * t, -1f);
        var d = _cam.GlobalBasis * dc;
        return _cam.GlobalPosition + d * ((y - _cam.GlobalPosition.Y) / d.Y);
    }

    float PlanoY() => _h.GlobalPosition.Y + ArqueiroStats.F("tiro_altura");

    static float Angulo(Vector3 a, Vector3 b)
    {
        a.Y = 0; b.Y = 0;
        return Mathf.RadToDeg(a.Normalized().AngleTo(b.Normalized()));
    }

    Arrow UltimaFlecha()
    {
        Arrow r = null;
        foreach (var n in GetTree().CurrentScene.GetChildren()) if (n is Arrow a) r = a;
        return r;
    }

    int ContaFlechas()
    {
        int c = 0;
        foreach (var n in GetTree().CurrentScene.GetChildren()) if (n is Arrow) c++;
        return c;
    }

    async System.Threading.Tasks.Task Teleporta(Vector3 p)
    {
        _h.GlobalPosition = p; _h.Velocity = Vector3.Zero; _h.ResetPhysicsInterpolation();
        await Espera(0.9f); // a câmera (suavizada) alcança
    }

    /// <summary>Segura o botão (mouse) em px, solta e mede a direção real da flecha. Devolve o erro em graus ou -1.</summary>
    async System.Threading.Tasks.Task<float> AtiraMouse(Vector2 px, float segura = 0.9f)
    {
        Clique(px, true);
        await Espera(segura);
        var dirMira = _h.DirMira;
        Clique(px, false);
        Arrow f = null;
        for (int i = 0; i < 30 && f == null; i++) { await Fisica(); f = UltimaFlecha(); }
        if (f == null) return -1f;
        var p0 = f.GlobalPosition;
        await Fisica(1);
        if (!IsInstanceValid(f)) return -1f;
        float err = Angulo(f.GlobalPosition - p0, dirMira);
        GD.Print($"TESTE:   flecha ativa; dir_real vs DirMira = {err:0.00} graus");
        return err;
    }

    public override async void _Ready()
    {
        _dir = ProjectSettings.GlobalizePath("res://capturas_arqueiro/");
        DirAccess.MakeDirRecursiveAbsolute(_dir);
        _h = GetParent().GetNode<ArqueiroController>("Arqueiro");
        _cam = GetParent().GetNode<CameraArqueiro>("CameraArqueiro");
        _cenaDummy = GD.Load<PackedScene>("res://scenes/arqueiro/Dummy.tscn");
        await Espera(1.5f);
        for (int i = 0; i < 300 && !_h.IsOnFloor(); i++) await Fisica();
        var spawn = _h.GlobalPosition;
        GD.Print($"TESTE: fps={Engine.GetFramesPerSecond()} corpo_real={_h.Modular.CorpoReal} clipe={_h.ClipeAtual} no_chao={_h.IsOnFloor()} pos={_h.GlobalPosition}");
        GD.Print($"TESTE: janela={DisplayServer.WindowGetSize()} viewport={GetViewport().GetVisibleRect().Size} mouse_mode={Input.MouseMode}");
        Foto("01_parado");

        // ---------- corrida: 2 quadros + velocidade e escala do clipe
        var p0 = _h.GlobalPosition;
        Input.ActionPress("move_up");
        await Espera(0.9f);
        Foto("02_andando");
        var ap = _h.Modular.Animacoes;
        GD.Print($"TESTE: corrida clipe={_h.ClipeAtual} vel={_h.Velocity.Length():0.00} m/s escala_clipe={(ap != null ? ap.SpeedScale : 0f):0.00} (ref Run {ArqueiroStats.F("anim_ref_correr")} m/s)");
        await Espera(0.17f);
        Foto("02b_andando");
        GD.Print($"TESTE: andou {(_h.GlobalPosition - p0).Length():0.00} m");
        Input.ActionRelease("move_up");
        await Espera(0.6f);

        // ---------- esquiva (i-frames vêm dos eventos do clipe)
        await Teleporta(spawn);
        p0 = _h.GlobalPosition;
        Input.ActionPress("move_right");
        Input.ActionPress("dodge");
        await Espera(0.02f);
        Input.ActionRelease("dodge");
        GD.Print($"TESTE: esquiva em ~0,02 s: iframe={_h.Invulneravel} (esperado false: evento ini no quadro {ArqueiroStats.F("evt_esq_iframe_ini_quadro")}/{ArqueiroStats.F("evt_esq_quadros")})");
        await Espera(0.13f);
        Foto("03_esquiva");
        GD.Print($"TESTE: esquiva em ~0,15 s: estado={_h.EstadoAtual} iframe={_h.Invulneravel} (esperado true)");
        await Espera(0.24f);
        GD.Print($"TESTE: esquiva em ~0,39 s: estado={_h.EstadoAtual} iframe={_h.Invulneravel}");
        Input.ActionRelease("move_right");
        await Espera(0.1f);
        GD.Print($"TESTE: esquiva deslocou {(_h.GlobalPosition - p0).Length():0.00} m");
        Input.ActionPress("dodge");
        await Espera(0.05f);
        Input.ActionRelease("dodge");
        await Espera(0.1f);
        GD.Print($"TESTE: esquiva em recarga (~0,65 s) bloqueada={_h.EstadoAtual != Estado.Esquiva}");
        await Espera(1.0f);

        // ---------- MIRA COM MOUSE REAL: ponto do mundo -> pixel -> evento -> ponto de mira -> flecha -> dummy
        var fracoes = new[] { new Vector2(0.66f, 0.14f), new Vector2(0.34f, 0.14f), new Vector2(0.50f, 0.07f) };
        int k = 0;
        foreach (var fr in fracoes)
        {
            k++;
            await Teleporta(spawn);
            var px = GetViewport().GetVisibleRect().Size * fr;
            var mundo = PontoIndep(px, PlanoY());
            var a = mundo;
            Mouse(px);
            await Fisica(3);
            var esp = PontoIndep(px, PlanoY());
            var pm = _h.PontoMira;
            float e1 = new Vector2(pm.X - esp.X, pm.Z - esp.Z).Length();
            float e2 = new Vector2(pm.X - mundo.X, pm.Z - mundo.Z).Length();
            GD.Print($"TESTE: mouse#{k} px=({px.X:0},{px.Y:0}) alvo=({a.X:0.00},{a.Z:0.00}) mira=({pm.X:0.00},{pm.Z:0.00}) indep=({esp.X:0.00},{esp.Z:0.00}) erro_indep={e1:0.000} m erro_alvo={e2:0.000} m");
            var d = _cenaDummy.Instantiate<Dummy>();
            GetParent().AddChild(d);
            d.GlobalPosition = new Vector3(a.X, _h.GlobalPosition.Y - 1f, a.Z);
            await Fisica(3);
            float hp0 = d.Hp;
            if (k == 1)
            {
                Clique(px, true); await Espera(0.5f); Foto("04_carregando"); Clique(px, false);
                await Espera(1.2f);
                GD.Print($"TESTE: mouse#{k} (carga parcial) dummy_novo hp {hp0} -> {d.Hp}");
                hp0 = d.Hp;
            }
            float err = await AtiraMouse(px);
            if (k == 1) Foto("05_disparo");
            await Espera(1.2f);
            GD.Print($"TESTE: mouse#{k} flecha_erro={err:0.00} graus dummy_novo hp {hp0} -> {d.Hp} acertou={d.Hp < hp0 || d.Morto} estado={_h.EstadoAtual} disparos={_h.Disparos}");
            d.QueueFree();
        }

        // câmera em movimento com o mouse parado na tela
        {
            await Teleporta(spawn);
            var px = _cam.UnprojectPosition(new Vector3(spawn.X + 3, PlanoY(), spawn.Z - 7));
            Mouse(px);
            Input.ActionPress("move_up");
            float maxErro = 0f; var primeiro = _h.PontoMira; Vector3 ultimo = primeiro;
            float somaErro = 0f; int nErro = 0;
            for (int i = 0; i < 60; i++)
            {
                await Fisica();
                if (i < 5) continue; // o evento injetado entra no proximo quadro
                var esp = PontoIndep(px, PlanoY());
                var pm = _h.PontoMira;
                float er = new Vector2(pm.X - esp.X, pm.Z - esp.Z).Length(); maxErro = Mathf.Max(maxErro, er); somaErro += er; nErro++;
                ultimo = pm;
            }
            GD.Print($"TESTE: mira com camera em movimento: pos_heroi={_h.GlobalPosition} erro_max={maxErro:0.000} m erro_medio={somaErro / Mathf.Max(nErro, 1):0.000} m fps={Engine.GetFramesPerSecond()}; ponto de mira andou {(ultimo - primeiro).Length():0.00} m (esperado >0: mouse parado, mundo corre)");
            Clique(px, true); await Espera(0.5f);
            var dm = _h.DirMira; Clique(px, false);
            Arrow f = null; for (int i = 0; i < 30 && f == null; i++) { await Fisica(); f = UltimaFlecha(); }
            if (f != null) { var q0 = f.GlobalPosition; await Fisica(3); if (IsInstanceValid(f)) GD.Print($"TESTE:   tiro andando: dir_real vs DirMira = {Angulo(f.GlobalPosition - q0, dm):0.00} graus"); }
            Input.ActionRelease("move_up");
            await Espera(1.0f);
        }

        // ---------- analógico direito e gamepad (eventos de joypad injetados)
        {
            await Teleporta(spawn);
            Eixo(JoyAxis.RightX, 1f);
            await Fisica(3);
            var b = _cam.GlobalBasis; var dd = b.X; dd.Y = 0;
            GD.Print($"TESTE: analogico direito x=+1: DirMira={_h.DirMira} erro vs direita da camera={Angulo(_h.DirMira, dd):0.00} graus");
            Eixo(JoyAxis.RightX, 0f); Eixo(JoyAxis.RightY, -1f);
            await Fisica(3);
            var ff = -b.Z; ff.Y = 0;
            GD.Print($"TESTE: analogico direito y=-1: DirMira={_h.DirMira} erro vs frente da camera={Angulo(_h.DirMira, ff):0.00} graus");
            Eixo(JoyAxis.RightY, 0f);

            var g0 = _h.GlobalPosition;
            Eixo(JoyAxis.LeftY, -1f);
            await Espera(0.6f);
            var desl = _h.GlobalPosition - g0;
            Eixo(JoyAxis.LeftY, 0f);
            GD.Print($"TESTE: gamepad esquerdo y=-1: deslocou {desl.Length():0.00} m, angulo vs frente da camera {Angulo(desl, ff):0.00} graus");
            await Espera(0.5f);

            Eixo(JoyAxis.RightX, 1f);
            Eixo(JoyAxis.TriggerRight, 1f);
            await Espera(0.3f);
            GD.Print($"TESTE: gatilho direito 1.0: estado={_h.EstadoAtual} carga={_h.Carga01:0.00}");
            int d0 = _h.Disparos;
            Eixo(JoyAxis.TriggerRight, 0f);
            await Espera(0.3f);
            GD.Print($"TESTE: gatilho solto: disparos {d0} -> {_h.Disparos}");
            Eixo(JoyAxis.RightX, 0f);
            await Espera(0.5f);
            Botao(JoyButton.B, true);
            await Fisica(2);
            GD.Print($"TESTE: botao B: estado={_h.EstadoAtual}");
            Botao(JoyButton.B, false);
            await Espera(1.2f);
        }

        // ---------- flecha cravada na parede (mira por mouse na parede mais próxima)
        {
            await Teleporta(spawn);
            // alvo: uma parede de verdade voltada para a camera (normal horizontal, de frente para +x+z), a 4-8 m de um ponto
            // livre perto do spawn; o heroi e levado para la. (Os pilares da Cripta nao tem colisao: a flecha os atravessa.)
            var space = _h.GetWorld3D().DirectSpaceState;
            Vector3? melhor = null; float dmin = 1e9f; Vector3 heroiPos = spawn;
            for (int gx = -6; gx <= 6 && melhor == null; gx++)
                for (int gz = -6; gz <= 6 && melhor == null; gz++)
                {
                    var pos = new Vector3(spawn.X + gx * 2.5f, spawn.Y, spawn.Z + gz * 2.5f);
                    var o = pos + Vector3.Up * ArqueiroStats.F("tiro_altura");
                    var chao = space.IntersectRay(PhysicsRayQueryParameters3D.Create(pos + Vector3.Up * 0.5f, pos + Vector3.Down * 1f, Camadas.Mundo));
                    if (chao.Count == 0) continue;
                    for (int a = 0; a < 360 && melhor == null; a += 15)
                    {
                        var dv = new Vector3(Mathf.Sin(Mathf.DegToRad(a)), 0, Mathf.Cos(Mathf.DegToRad(a)));
                        var r = space.IntersectRay(PhysicsRayQueryParameters3D.Create(o, o + dv * 6f, Camadas.Mundo));
                        if (r.Count == 0) continue;
                        var n = (Vector3)r["normal"]; var hp = (Vector3)r["position"];
                        float dist = (hp - o).Length();
                        if (dist >= 3.5f && Mathf.Abs(n.Y) < 0.5f && n.Dot(new Vector3(0.707f, 0, 0.707f)) > 0.4f)
                        { melhor = hp; dmin = dist; heroiPos = pos; }
                    }
                }
            if (melhor is Vector3 w)
            {
                GD.Print($"TESTE: alvo de parede/pilar a {dmin:0.0} m em {w}");
                await Teleporta(heroiPos);
                w.Y = PlanoY();
                var px = _cam.UnprojectPosition(w);
                Mouse(px);
                await Fisica(3);
                await AtiraMouse(px);
                await Espera(0.5f);
                var fl = UltimaFlecha();
                GD.Print($"TESTE: flecha na parede: existe={fl != null} cravada={fl?.Cravada} flechas={ContaFlechas()} pos_flecha={fl?.GlobalPosition} heroi={_h.GlobalPosition} pilar={w}");
                if (fl != null)
                {
                    Foto("06_flecha_parede");
                    Recorte("06b_flecha_parede_recorte", fl.GlobalPosition);
                    await Espera(3.0f);
                    GD.Print($"TESTE: flecha apos ~3,5 s: existe={IsInstanceValid(fl)} flechas={ContaFlechas()}");
                    if (IsInstanceValid(fl)) Recorte("06c_flecha_parede_3s", fl.GlobalPosition);
                    await Espera(1.5f);
                    GD.Print($"TESTE: flecha apos ~5 s: flechas={ContaFlechas()} (esperado 0)");
                }
            }
            else GD.Print("TESTE: nenhuma parede a menos de 10 m do spawn");
        }

        // ---------- dano e morte
        await Teleporta(spawn);
        _h.ReceberDano(20f, _h.GlobalPosition + Vector3.Back);
        await Espera(0.15f);
        GD.Print($"TESTE: dano estado={_h.EstadoAtual} hp={_h.Hp}");
        Foto("07_dano");
        await Espera(1.0f);
        _h.ReceberDano(1000f, _h.GlobalPosition);
        await Espera(0.6f);
        GD.Print($"TESTE: morte estado={_h.EstadoAtual} hp={_h.Hp} clipe={_h.ClipeAtual}");
        Foto("08_morte");
        _h.Renascer();
        GD.Print("TESTE: FIM");
        GetTree().Quit();
    }
}
