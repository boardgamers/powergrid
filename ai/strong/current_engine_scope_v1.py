"""Declared scope for the current-engine confirmation, before any inference.

This is not a production router. Unsupported games fail explicitly instead of
silently receiving predictions from an unvalidated representation.
"""


def validate_request_scope(request):
    state = request['state']
    options = state.get('options', {})
    allowed = {'map', 'variant', 'fastBid', 'showMoney', 'useNewRechargedSetup',
               'endPlantDiscountAtStep3', 'trackTotalSpent', 'randomizeMap',
               'chooseRegions', 'chooseColors', 'alternatePowerPlants'}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError('Unrecognized game options in current-engine research scope')
    if state.get('map', {}).get('name') != 'Germany' or options.get('map', 'Germany') != 'Germany':
        raise ValueError('Current-engine confirmation supports Germany only')
    if options.get('variant') not in ('original', 'recharged'):
        raise ValueError('Expected explicit original or recharged variant')
    for name in allowed - {'map', 'variant'}:
        if name in options and type(options[name]) is not bool:
            raise ValueError('Expected Boolean game option: ' + name)
    if options.get('showMoney') is not True or type(options.get('fastBid')) is not bool:
        raise ValueError('Research policy requires public money and explicit auction mode')
    for name in ('endPlantDiscountAtStep3', 'randomizeMap', 'chooseRegions',
                 'chooseColors', 'alternatePowerPlants'):
        if options.get(name, False):
            raise ValueError('Unsupported confirmation option: ' + name)
    if options['variant'] == 'recharged' and options.get('useNewRechargedSetup', True) is not True:
        raise ValueError('Confirmation uses the current Recharged setup')
    if any(type(p.get('money')) is not int or p['money'] < 0 for p in state['players']):
        raise ValueError('Every player balance must be public')
    if state.get('regionDraft') or state.get('colorDraft'):
        raise ValueError('Drafting is outside the automatic-setup confirmation')

