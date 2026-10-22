"""Resolve exact SEC ticker symbols before fuzzy company-name search."""


class CompanyDirectory:
    def __init__(self, companies):
        self.companies=companies
        self.tickers={}
        for company in companies:
            self.tickers.setdefault(company['ticker'].upper(),[]).append(company)

    def resolve(self, query):
        query=query.strip()
        ticker=query.upper()
        # Literal exact symbol always precedes aliases AND company-name matches.
        if ticker in self.tickers:
            return self.tickers[ticker]
        # Vendor share-class punctuation is only a fallback when no literal symbol exists.
        alias=ticker.replace('.','-')
        if alias in self.tickers:
            return self.tickers[alias]
        if query.isdigit():
            return [c for c in self.companies if int(c['cik_str'])==int(query)]
        named=[c for c in self.companies if c['title'].casefold()==query.casefold()]
        if named:
            return named
        return [c for c in self.companies if query.casefold() in c['title'].casefold()] if query else []


def resolve_companies(companies, query):
    return CompanyDirectory(companies).resolve(query)
