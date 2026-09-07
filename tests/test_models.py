from app.models import Evidence, Fact, Relation

def test_fact_requires_grounded_evidence():
    e=Evidence(document_id="abc",filename="a.pdf",page=1,quote="Revenue was $10M",char_start=0,char_end=17)
    f=Fact(id="1",subject="Company",predicate="revenue",value="$10M",evidence=e,confidence=.9)
    assert f.evidence.verified is True

def test_relation_values_are_explicit():
    assert {x.value for x in Relation} == {"Corroborated","Contradicted","Context-Resolved","Related"}
