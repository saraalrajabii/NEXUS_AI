from app.config import Settings


def test_single_database_url_is_used_with_psycopg_driver():
    s = Settings(nexus_database_url="postgresql://u:p@db.internal:5432/railway")
    url = s.database_url()
    assert (url.drivername, url.host, url.database) == ("postgresql+psycopg", "db.internal", "railway")
    assert s.database_url("other").database == "other"


def test_parts_are_used_when_no_url_given():
    s = Settings(nexus_database_url="", nexus_db_host="nexus-db", nexus_db_name="nexus")
    assert (s.database_url().host, s.database_url().database) == ("nexus-db", "nexus")
