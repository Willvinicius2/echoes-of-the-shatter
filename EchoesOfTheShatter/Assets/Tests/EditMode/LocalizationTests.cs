using System.IO;
using Echoes.Core;
using NUnit.Framework;

namespace Echoes.Tests.EditMode
{
    [Category("Loc")]
    public sealed class LocalizationTests
    {
        [Test]
        public void CsvReaderHandlesQuotesCommasNewlinesAndUtf8()
        {
            // Loc.CsvReaderQuotesCommasUtf8 (seção 13.2 do 04).
            var text = "﻿key,pt_BR,en\r\nui.a,\"Ação, coração\",\"Say \"\"hi\"\"\"\nui.b,\"duas\nlinhas\",two\n";
            var records = CsvReader.Parse(text);
            Assert.AreEqual(3, records.Count);
            CollectionAssert.AreEqual(new[] { "key", "pt_BR", "en" }, records[0].Fields);
            Assert.AreEqual("Ação, coração", records[1].Fields[1]);
            Assert.AreEqual("Say \"hi\"", records[1].Fields[2]);
            Assert.AreEqual("duas\nlinhas", records[2].Fields[1]);
            Assert.AreEqual(3, records[2].Line);
        }

        [Test]
        public void FallsBackToEnglishThenToTheKey()
        {
            // Loc.FallbackToEn: cultura sem tradução cai em en; chave ausente devolve a própria chave.
            var warnings = 0;
            var loc = new LocalizationService(_ => warnings++);
            loc.Table.AddCsv("key,pt_BR,en,es,context,gender\nui.a,Vida,Life,,hud,\nui.b,,Only en,,hud,\n");
            loc.SetCulture("pt_BR");
            Assert.AreEqual("Vida", loc.Get("ui.a"));
            Assert.AreEqual("Only en", loc.Get("ui.b"));
            Assert.AreEqual("ui.missing", loc.Get("ui.missing"));
            Assert.AreEqual(1, warnings);
            loc.Get("ui.missing");
            Assert.AreEqual(1, warnings, "avisa uma vez por chave");
        }

        [Test]
        public void UnknownCultureUsesEnglish()
        {
            var loc = new LocalizationService(null);
            loc.Table.AddCsv("key,pt_BR,en\nui.a,Vida,Life\n");
            loc.SetCulture("fr");
            Assert.AreEqual("en", loc.Culture);
            Assert.AreEqual("Life", loc.Get("ui.a"));
        }

        [Test]
        public void MapsSystemLanguage()
        {
            Assert.AreEqual("pt_BR", LocalizationTable.CultureColumnFor("pt-BR"));
            Assert.AreEqual("pt_BR", LocalizationTable.CultureColumnFor("pt"));
            Assert.AreEqual("en", LocalizationTable.CultureColumnFor("fr-FR"));
        }

        [Test]
        public void FormatsNumbersInTheCulture()
        {
            var loc = new LocalizationService(null);
            loc.Table.AddCsv("key,pt_BR,en\nui.a,Vida,Life\n");
            loc.SetCulture("pt_BR");
            Assert.AreEqual("1.234", loc.FormatInteger(1234));
            Assert.AreEqual("0,8", loc.FormatDecimal(0.8, 1));
        }

        [Test]
        public void HudKeysExistInPtBrAndEn()
        {
            // Chaves usadas pelo HudView.uxml e pelo HudView.cs (RF-61): precisam existir nas duas colunas.
            var loc = new LocalizationService(null);
            loc.LoadDirectory(Path.Combine(TestWorld.DataDirectory, "Loc"));
            foreach (var culture in new[] { "pt_BR", "en" })
            {
                foreach (var key in new[] { "ui.death.title", "ui.death.checkpoint", "dodge.name", "ui.hud.no_resource", "ui.hud.potion_empty", "skill.warrior.iron_cut.name" })
                {
                    Assert.IsTrue(loc.Table.TryGet(culture, key, out var text) && text.Length > 0, $"{culture}: {key}");
                }
            }
        }
    }
}
