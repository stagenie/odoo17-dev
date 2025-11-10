# -*- coding: utf-8 -*-
# Part of ADI Cost Management Module

# IMPORTANT : L'ordre d'import est crucial !
# Les modèles de base doivent être importés avant les vues SQL

from . import adi_daily_production  # 1er : modèle principal
from . import adi_scrap_management  # 2ème : modèle des rebuts
from . import adi_cost_analysis     # DERNIER : vue SQL qui dépend des autres
