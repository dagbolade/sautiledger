import pytest
from sautiledger.agent import Agent
from sautiledger.ledger import Ledger
from sautiledger.packs import load_pack
from sautiledger.normaliser import normalise

TEENS = ['eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen']

@pytest.mark.parametrize('word,value', list(zip(TEENS,range(11,20))))
@pytest.mark.parametrize('each',[False,True])
def test_teen_thousands_reach_ledger_without_losing_multiplier(word,value,each):
    a=Agent(load_pack('pcm-yo-NG'),Ledger(':memory:'))
    a.handle(f'I sell 2 cup of rice for {word} thousand naira'+(' each' if each else ''))
    a.handle('yes')
    row=a.ledger.last_transaction()
    assert row['amount']==value*1000*(2 if each else 1)
    assert row['item']=='rice' and a.pending is None and not a.awaiting_confirm


def test_yoruba_paid_transport_is_expense():
    a=Agent(load_pack('pcm-yo-NG'),Ledger(':memory:'))
    a.handle('Mo san transport fare two thousand naira')
    a.handle('yes')
    a.handle('yes')
    row=a.ledger.last_transaction()
    assert (row['type'],row['item'],row['amount'])==('expense','transport fare',2000)
    assert a.ledger.sales_total('today')[1]==0


def test_explicit_thousands_hundreds_and_shorthand_agree():
    p=load_pack('pcm-yo-NG')
    for phrase in ['four thousand five hundred','four thousand five']:
        r=normalise('I sell rice for '+phrase+' naira',p)
        assert r.amount==4500 and r.item=='rice'


def test_yoruba_sales_question_does_not_write():
    a=Agent(load_pack('pcm-yo-NG'),Ledger(':memory:'))
    a.handle('I sell rice for 4500 naira');a.handle('yes')
    before=[dict(r) for r in a.ledger.all_transactions()]
    reply=a.handle('Elo ni mo ta loni')
    assert 'four thousand five hundred' in reply
    assert [dict(r) for r in a.ledger.all_transactions()]==before
    assert a.pending is None and not a.awaiting_confirm

