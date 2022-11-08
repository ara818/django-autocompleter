from django.db import models


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    market_cap = models.FloatField(null=True, blank=True)
    sector = models.CharField(max_length=200, default='')
    industry = models.CharField(max_length=200, default='')
    hidden = models.BooleanField(default=False)


class Indicator(models.Model):
    name = models.CharField(max_length=200, unique=True)
    internal_name = models.CharField(max_length=200, unique=True)
    score = models.FloatField(null=True, blank=True)


class CalcList(models.Model):
    name = models.CharField(max_length=200, unique=True)


class CalcListItem(models.Model):
    calc_list = models.ForeignKey(CalcList, on_delete=models.CASCADE)
    calc_name = models.CharField(max_length=200)
