"""
Comprehensive tests for whistle DSL — parser, compiler, validator.
"""

import pytest
from whistle import parse, compile as whistle_compile, validate
from whistle.parser import Schedule, Trigger, WhistleProgram
from whistle.compiler import compile_one
from whistle.validator import ValidationResult


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_simple_whistle(self):
        src = '''
        whistle simple {
            breed: "gpt-4",
            pasture: "test-room"
        }
        '''
        prog = parse(src)
        assert len(prog.statements) == 1
        stmt = prog.statements[0]
        assert stmt.name == "simple"
        assert stmt.get("breed") == "gpt-4"
        assert stmt.get("pasture") == "test-room"

    def test_multiple_statements(self):
        src = '''
        whistle first {
            breed: "gpt-4"
        }
        whistle second {
            breed: "claude-3-opus"
        }
        '''
        prog = parse(src)
        assert len(prog.statements) == 2
        assert prog.statements[0].name == "first"
        assert prog.statements[1].name == "second"

    def test_all_fields(self):
        src = '''
        whistle full {
            breed: "gpt-4",
            pasture: "medical-review",
            fence: "conservation/budget_decay.bin",
            herd: "medical-records",
            rotate: every_30_min,
            recall: on_alarm,
            flank: "preprocessor-v2",
            drive: "inbound",
            stock: "3:1"
        }
        '''
        prog = parse(src)
        stmt = prog.statements[0]
        assert stmt.get("breed") == "gpt-4"
        assert stmt.get("pasture") == "medical-review"
        assert stmt.get("fence") == "conservation/budget_decay.bin"
        assert stmt.get("herd") == "medical-records"
        assert isinstance(stmt.get("rotate"), Schedule)
        assert isinstance(stmt.get("recall"), Trigger)
        assert stmt.get("flank") == "preprocessor-v2"
        assert stmt.get("drive") == "inbound"
        assert stmt.get("stock") == "3:1"

    def test_schedule_minutes(self):
        src = 'whistle t { breed: "gpt-4", rotate: every_30_min }'
        prog = parse(src)
        sched = prog.statements[0].get("rotate")
        assert isinstance(sched, Schedule)
        assert sched.interval_seconds == 30 * 60
        assert sched.kind == "interval"

    def test_schedule_hours(self):
        src = 'whistle t { breed: "gpt-4", rotate: every_2_hours }'
        prog = parse(src)
        sched = prog.statements[0].get("rotate")
        assert isinstance(sched, Schedule)
        assert sched.interval_seconds == 2 * 3600

    def test_schedule_daily(self):
        src = 'whistle t { breed: "gpt-4", rotate: every_day_at_09:00 }'
        prog = parse(src)
        sched = prog.statements[0].get("rotate")
        assert isinstance(sched, Schedule)
        assert sched.kind == "daily"
        assert sched.at_time == "09:00"
        assert sched.interval_seconds == 86400

    def test_trigger(self):
        src = 'whistle t { breed: "gpt-4", recall: on_drift }'
        prog = parse(src)
        trig = prog.statements[0].get("recall")
        assert isinstance(trig, Trigger)
        assert trig.event == "drift"

    def test_comments_stripped(self):
        src = '''
        # This is a comment
        whistle t {
            breed: "gpt-4",  # inline comment
            pasture: "room"
        }
        '''
        prog = parse(src)
        assert prog.statements[0].get("breed") == "gpt-4"

    def test_trailing_comma_optional(self):
        src_no_comma = 'whistle t { breed: "gpt-4", pasture: "a" }'
        src_comma = 'whistle t { breed: "gpt-4", pasture: "a", }'
        p1 = parse(src_no_comma)
        p2 = parse(src_comma)
        assert p1.statements[0].get("pasture") == p2.statements[0].get("pasture")

    def test_no_trailing_newline(self):
        src = 'whistle t { breed: "gpt-4" }'
        prog = parse(src)
        assert len(prog.statements) == 1

    def test_find_by_name(self):
        src = 'whistle alpha { breed: "gpt-4" }'
        prog = parse(src)
        assert prog.find("alpha") is not None
        assert prog.find("beta") is None

    def test_missing_brace_raises(self):
        src = 'whistle t { breed: "gpt-4"'
        with pytest.raises(SyntaxError):
            parse(src)

    def test_missing_colon_raises(self):
        src = 'whistle t { breed "gpt-4" }'
        with pytest.raises(SyntaxError):
            parse(src)

    def test_missing_whistle_keyword_raises(self):
        src = 't { breed: "gpt-4" }'
        with pytest.raises(SyntaxError):
            parse(src)

    def test_unterminated_string_raises(self):
        src = 'whistle t { breed: "gpt-4 }'
        with pytest.raises(SyntaxError):
            parse(src)

    def test_empty_program(self):
        prog = parse("")
        assert len(prog.statements) == 0

    def test_number_value(self):
        src = 'whistle t { breed: "gpt-4", stock: 3 }'
        prog = parse(src)
        assert prog.statements[0].get("stock") == 3

    def test_bare_identifier_value(self):
        src = 'whistle t { breed: "gpt-4", drive: inbound }'
        prog = parse(src)
        assert prog.statements[0].get("drive") == "inbound"


# ---------------------------------------------------------------------------
# Compiler tests
# ---------------------------------------------------------------------------

class TestCompiler:
    def test_compile_basic(self):
        src = '''
        whistle med {
            breed: "gpt-4",
            pasture: "medical-review",
            herd: "records"
        }
        '''
        prog = parse(src)
        result = whistle_compile(prog)
        assert "whistles" in result
        assert "med" in result["whistles"]
        cfg = result["whistles"]["med"]
        assert cfg["plato"]["model"] == "gpt-4"
        assert cfg["plato"]["room"] == "medical-review"
        assert cfg["plato"]["corpus"] == "records"

    def test_compile_flux_known_breed(self):
        src = 'whistle t { breed: "claude-3-opus" }'
        prog = parse(src)
        result = whistle_compile(prog)
        flux = result["whistles"]["t"]["flux"]
        assert flux["routing"]["provider"] == "anthropic"
        assert flux["routing"]["family"] == "claude-3"
        assert flux["routing"]["context_window"] == 200_000

    def test_compile_flux_unknown_breed(self):
        src = 'whistle t { breed: "custom-model-x" }'
        prog = parse(src)
        result = whistle_compile(prog)
        flux = result["whistles"]["t"]["flux"]
        assert flux["routing"]["provider"] == "unknown"

    def test_compile_conservation_fence(self):
        src = '''
        whistle t {
            breed: "gpt-4",
            fence: "conservation/budget_decay.bin"
        }
        '''
        prog = parse(src)
        result = whistle_compile(prog)
        cons = result["whistles"]["t"]["conservation"]
        assert cons["policy_file"] == "conservation/budget_decay.bin"
        assert cons["enforcer"] == "conservation.BudgetDecay"

    def test_compile_no_fence(self):
        src = 'whistle t { breed: "gpt-4" }'
        prog = parse(src)
        result = whistle_compile(prog)
        cons = result["whistles"]["t"]["conservation"]
        assert cons["enforcer"] is None

    def test_compile_schedule_interval(self):
        src = 'whistle t { breed: "gpt-4", rotate: every_45_min }'
        prog = parse(src)
        result = whistle_compile(prog)
        sched = result["whistles"]["t"]["schedule"]
        assert sched["type"] == "interval"
        assert sched["interval_seconds"] == 45 * 60

    def test_compile_schedule_daily(self):
        src = 'whistle t { breed: "gpt-4", rotate: every_day_at_14:30 }'
        prog = parse(src)
        result = whistle_compile(prog)
        sched = result["whistles"]["t"]["schedule"]
        assert sched["type"] == "daily"
        assert sched["at_time"] == "14:30"

    def test_compile_recall(self):
        src = 'whistle t { breed: "gpt-4", recall: on_budget }'
        prog = parse(src)
        result = whistle_compile(prog)
        rec = result["whistles"]["t"]["recall"]
        assert rec["trigger"] == "budget"
        assert rec["action"] == "halt_and_return"

    def test_compile_optional_fields(self):
        src = '''
        whistle t {
            breed: "gpt-4",
            flank: "preproc-v2",
            drive: "outbound",
            stock: "5:1"
        }
        '''
        prog = parse(src)
        result = whistle_compile(prog)
        cfg = result["whistles"]["t"]
        assert cfg["flux"]["preprocessor"] == "preproc-v2"
        assert cfg["flux"]["stock_ratio"] == "5:1"
        assert cfg["plato"]["drive"] == "outbound"

    def test_compile_one_single(self):
        src = 'whistle solo { breed: "gpt-4" }'
        prog = parse(src)
        cc = compile_one(prog.statements[0])
        assert cc.name == "solo"
        assert cc.plato["model"] == "gpt-4"

    def test_compile_raw_passthrough(self):
        src = '''
        whistle t {
            breed: "gpt-4",
            pasture: "room",
            custom_field: "hello"
        }
        '''
        prog = parse(src)
        result = whistle_compile(prog)
        raw = result["whistles"]["t"]["raw"]
        assert raw["custom_field"] == "hello"

    def test_compile_multiple_whistles(self):
        src = '''
        whistle a { breed: "gpt-4" }
        whistle b { breed: "claude-3-opus" }
        '''
        prog = parse(src)
        result = whistle_compile(prog)
        assert "a" in result["whistles"]
        assert "b" in result["whistles"]
        assert result["whistles"]["a"]["flux"]["breed"] == "gpt-4"
        assert result["whistles"]["b"]["flux"]["breed"] == "claude-3-opus"


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_program(self):
        src = '''
        whistle good {
            breed: "gpt-4",
            pasture: "room",
            fence: "conservation/p.bin",
            herd: "data",
            rotate: every_30_min,
            recall: on_alarm
        }
        '''
        prog = parse(src)
        result = validate(prog)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_breed_is_error(self):
        src = 'whistle bad { pasture: "room" }'
        prog = parse(src)
        result = validate(prog)
        assert not result.valid
        assert any(e.field == "breed" for e in result.errors)

    def test_unknown_breed_is_warning(self):
        src = 'whistle t { breed: "totally-fake-model" }'
        prog = parse(src)
        result = validate(prog)
        assert result.valid  # warnings don't block
        assert any(
            w.field == "breed" and "custom" in w.message
            for w in result.warnings
        )

    def test_empty_pasture_is_error(self):
        src = 'whistle t { breed: "gpt-4", pasture: "" }'
        prog = parse(src)
        result = validate(prog)
        assert not result.valid

    def test_unknown_field_is_warning(self):
        src = 'whistle t { breed: "gpt-4", bogus_field: "x" }'
        prog = parse(src)
        result = validate(prog)
        assert result.valid
        assert any(w.field == "bogus_field" for w in result.warnings)

    def test_bad_drive_value_warns(self):
        src = 'whistle t { breed: "gpt-4", drive: "sideways" }'
        prog = parse(src)
        result = validate(prog)
        assert result.valid
        assert any(
            w.field == "drive" for w in result.warnings
        )

    def test_good_drive_no_warning(self):
        src = 'whistle t { breed: "gpt-4", drive: "inbound" }'
        prog = parse(src)
        result = validate(prog)
        assert not any(w.field == "drive" for w in result.warnings)

    def test_fence_path_warning(self):
        src = 'whistle t { breed: "gpt-4", fence: "justaname" }'
        prog = parse(src)
        result = validate(prog)
        assert result.valid
        assert any(
            w.field == "fence" and "path" in w.message
            for w in result.warnings
        )

    def test_valid_result_bool(self):
        src = 'whistle t { breed: "gpt-4" }'
        prog = parse(src)
        result = validate(prog)
        assert bool(result) is True

    def test_multiple_errors(self):
        src = '''
        whistle t {
            pasture: "",
            herd: ""
        }
        '''
        prog = parse(src)
        result = validate(prog)
        assert not result.valid
        assert len(result.errors) >= 3  # missing breed + empty pasture + empty herd


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_pipeline(self):
        """parse -> validate -> compile all succeed."""
        src = '''
        whistle daily_ops {
            breed: "claude-3-sonnet",
            pasture: "ops-briefing",
            fence: "conservation/strict.bin",
            herd: "ops-data",
            rotate: every_4_hours,
            recall: on_drift,
            flank: "summarizer",
            drive: "inbound"
        }
        '''
        prog = parse(src)
        vresult = validate(prog)
        assert vresult.valid
        config = whistle_compile(prog)
        cfg = config["whistles"]["daily_ops"]
        assert cfg["plato"]["room"] == "ops-briefing"
        assert cfg["conservation"]["enforcer"] == "conservation.BudgetDecay"
        assert cfg["flux"]["routing"]["provider"] == "anthropic"
        assert cfg["schedule"]["interval_seconds"] == 4 * 3600
        assert cfg["recall"]["trigger"] == "drift"

    def test_pipeline_with_warnings(self):
        """Programs with warnings still compile."""
        src = '''
        whistle experimental {
            breed: "my-finetune-v2",
            pasture: "lab",
            mystery_key: 42
        }
        '''
        prog = parse(src)
        vresult = validate(prog)
        assert vresult.valid
        assert len(vresult.warnings) >= 2  # unknown breed + unknown field
        config = whistle_compile(prog)
        assert "experimental" in config["whistles"]
