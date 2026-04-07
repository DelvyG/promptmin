from promptmin.engine import minify, available_domains, load_domain, load_domains
from promptmin.tokens import count


def test_available_domains_not_empty():
    domains = available_domains()
    assert "web" in domains
    assert "backend" in domains
    assert "devops" in domains
    assert "data" in domains
    assert "ai" in domains


def test_load_single_domain():
    web = load_domain("web")
    assert len(web) > 10
    assert "user experience" in web
    assert web["user experience"] == "UX"


def test_load_unknown_domain_returns_empty():
    assert load_domains(["doesnotexist"]) == {}


def test_domain_merges_with_precedence():
    merged = load_domains(["web", "backend"])
    assert "user experience" in merged  # from web
    assert "authentication" in merged   # from backend


def test_web_domain_saves_on_ux_phrase():
    text = "Please improve the user experience and user interface of the mobile responsive design."
    baseline = minify(text)
    with_web = minify(text, domains=["web"])
    assert count(with_web["minified"]) < count(baseline["minified"]), (
        f"web domain should save more. baseline={baseline['minified']!r} "
        f"with_web={with_web['minified']!r}"
    )


def test_domains_never_regress():
    """Core guarantee holds with domains active."""
    samples = [
        "Improve the user experience on mobile.",
        "Set up CI/CD with Kubernetes and Docker.",
        "Build a REST API with JWT authentication.",
        "Mejora la experiencia de usuario en móviles.",
        "Configura integración continua con Kubernetes.",
    ]
    for t in samples:
        res = minify(t, domains=available_domains())
        assert count(res["minified"]) <= count(t), f"regressed on {t!r}"
