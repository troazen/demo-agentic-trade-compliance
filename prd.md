# Overview 

*First, this project is to create an example application for testing and educaitonal purposes. It will not be a production application.*

 the purpose of this application will be to create a trade and portfolio compliance systemin the vein of the features in State Street's Charles River Development (CRD / CRIMS) or BlackRock's Aladdin. The goal of the system is to monitor compliance of trades placed in an open end 40 act mutual fund. As the orders are placed a set of custom coded compliance rules should be applied to each order for the fundand if any warn or alert we will notify the userrequiring the user to enter a comment before the transaction can proceed. This application is intended to be able to interact with agentic AI tools via its REST API (MCP may be added in future but is not needed at this time).
 

# Tech Stack

This applicaiton will use a Python Flask backend with a Streamlit front end. Speed of development and simplicty of code are key considerations, as this won't be production software used in a real business setting. The system will need a database, we'll use SQLite with Python as the client. 

## Architecture

This application will have the following components:

* Database containing all tables as described in this document, and any other tables necessary for operation. We will use SQLite for the database as this isn't an enterprise app and doesn't need to worry about numerous users. 
* Back-end server infrastructure provided by Flask, which will connect to the database using Flask-SQLAlchemy. The SQLAlchemy scripts should define all tables such that if the database isn't available, it is created, and if any table isn't available, it is created. 
* Front end using streamlit. 
* REST API to connect front and back end. REST API should be designed to be called externally. You may use Fast API, Flask, or any combination to provide the API service. API should be integrated to back-end server rather than being a separate service, if possible. 


## Data Security and Resilience 

As this is just a basic app for testing and educational use, it will not contain sensitive info. Please do not consider scalability, resilience for the future, or security. There is no need to follow the standard best practices, instead focus on quick and simple code with streamlined structures. When the server is running, any user who connects may use the application with full privilages, from the front-end or the API. 

## Deployment

This project will use docker container(s) set up via Docker Compose. We will get an MVP working and then set up the container(s). We expect to try and use just one container to contain both the app and the database, if possible. 

Data input and seeding at application startup will be determined in the near future. Our current plan is to create a SQLite database based on the needs of this application. Creating the seeding script is beyond the scope of this requirements document, for now, but we will add it as an enhancement later. 

## Trade Flow

**The trade process will work as follows:**
1. User places trade in UI or through API. Trade will be one of a BUY or SELL order, and will always involve one fund's holdings: cash, and one security. A BUY order will decrease cash and either create a new holding or increase the shares of an existing holding. A SELL order will increase cash and either remove an existing holding or decrease shares held by the fund. Note that we do not allow trading of fractional shares (number of shares to BUY or SELL will always be a whole number != 0)
2. We determine the inputs needed to execute the trade. We need the ticker to identify the security record, and the number of shares as a positive whole number. Short sales and other exotic transactions are not supported. These should be provided by the user and validated by the system, missing or invalid values result in the trade being rejected at this stage. If the trade has the baseline required details for input, a record will be created in the trades table for it, a trade_id (primary key) will be assigned, and the status will be 'submitted'.
3. We look up the current price from the securities_price table and multiply by the number of shares to get the total value of the trade in currency. Update the trade status to "validating". 
4. If a BUY order, we validate the fund has enough cash. ```SELECT cash FROM funds WHERE funds.fund_id = {trade.fund_id}``` must have a higher value than the total value of the trade. If cash is zero, no buy order would be allowed. 
5. If a SELL order, we validate the fund holds the same or more shares than the size of the order. ```SELECT shares FROM holdings INNER JOIN securities s ON s.ticker = holdings.ticker WHERE holdings.fund_id = {trade.fund_id} AND s.ticker = '{trade.ticker}'``` must have a higher value than the total shares in the trade. 
6. If any of the checks from the previous few steps fail, we notify the user (return an error code for the API) and reject the trade. This is not a compliance check and the user does not have an option to override or force the trade, they can only acknowledge by click OK on the error message in the UI (not needed for API). They will need to re-submit the trade as a valid order. We should notify the user in the error message or API response the specific check that failed and the reason, i.e. "Trading cash is not allowed" or "You tried to place a BUY order for 2000 shares of MSFT at a price of $515.48, which would cost $1,030,960; however, the fund only has $875,291.43 in cash, a shortfall of $155,668.57. Please adjust your order to 1,699 shares or fewer." We do not log an alert for these as they are not compliance checks. Trade status is updated to "invalid". 
7. Now that we have a theoretically valid trade, the next step is to check compliance. We start by copying all the funds holdings to the holdings_staging table, tagging each row with the trade_id (an additional column the holdings table does not have). While it may be inefficient to copy all holdings, we don't need to worry about the cost of storage and we can truncate this table at any time. We need a working copy of holdings we can edit to perform compliance checks. Update the status to 'compliance'.
8. Determine and store logic that would be needed to edit the holdings to reflect the trade. Please adhere to the following rules: 1) the "ticker" value must be unique for each fund and trade in the holdings_staging table, if we are executing a BUY for a security already present, increase shares of the existing position; 2) we do not store holdings with "0" shares, if we are executing a SELL of a security equal to the number of shares in holdings, will will remove that row from the holdings_staging table. Note that this logic and these rules should also apply to holdings table, when we get there. 
9. Execute the logic on the holdings_staging table for the holdings identified by fund_id and trade_id. Store logic for re-use later. 
10. Run all compliance rules returned by this query ```SELECT r.* FROM rules r INNER JOIN rules_attachements ra ON r.rule_id = ra.rule_id WHERE ra.fund_id = {trade.fund_id} AND r.active AND r.trade_compliance_mode``` See "Compliance Engine" for more details on running rules. Note that we want to run every rule and give the user a list of alerts, do not stop at the first rule which alerts run all of them. 
11. Present the user the list of alerts with the option to respond to each one. For trades submitted via the UI, the user can enter an override note for each and click "override" to proceed with the trade, or click "cancel" (which does not require any override reasons to be filled). The override or cancel should be present once, even if if multiple alerts. For trades submitted via the API, the submitter should get back a 403 with the body having JSON representation of all rule names, rule ID, and restults. The API caller can submit an override request for the trade ID with the body containing an override note for each alert. All alerts must be stored, with the override note if present and result (cancel or override). On the back-end, the moment the compliance rules alert the order is moved to a cancel state, so if the API caller never sends a follow-up or the user terminates their session before hitting "cancel", the cancel is the action taken. Only if the overide is explicitly given by the user do we change from "cancel" to "override" and allow the trade to proceed. The trade status will be updated to 'alert'; note that the "cancelled" status is intended for when a user cancels a trade for reasons other than a compliance alert, if the user chooses not to override the trade (regardless of whether the activley click cancel), the trade should stay at "alert" status. 
12. If there are no alerts or if the alerts are overridden, then we process the trade. We take the stored logic and apply to actual holdings (i.e. the same changes we made to holdings_staging are made to the fund's actual holdings). The order status will then change to "processed". Unlike a real-world production system, we do not need to worry about post-trade activities or settlement; we treat each trade as if it happens instantly during this step. 
13. As part of processing the trade, we also adjust cash (decrease for a BUY; increase for a SELL) in the funds table for the affected fund.
14. We notify the user that the trade executed successfully (popup in the UI, or 200 response with trade details in the API). *Note that from a user perspective, for a valid trade which passed all compliance checks, they would see the following in the UI 1) click button to initiate trade; 2) enter trade details (security, direction, amount of shares); 3) submit the trade; 4) after a short delay, they would get a popup that their order was successfully executed. In the API they would submit the trade details, and get back a 200 with the trade details in the body, and a notice of successful execution.*


## Compliance Engine

Core to the back-end logic of this application will be the compliance engine, which tests compliance rules against trades and holdings. Each compliance rule will have an attachment to one or more funds, and will have two mode flags set to True or False in the logic. The first mode will check compliance against holdings when "batch" check is run (triggered manually by user). The second mode is trade compliance, which if True will check compliance against the holdings with the proposed trade included whenever a trade is attempted. 

Each rule will have logic, which should function as the WHERE clause of a SQL statement that selects from a join of the holdings, security, and issuer tables. You may think of the rule logic as being part of a larger SQL SELECT statement, functioning as the WHERE clause. 
Note that if the rule is being run against a BUY or SELL order, we should treat the holdings as what they would be if the order were completed (so if a compliance rule would limit a holding to 1000 shares, we have 800 in the fund already, and a BUY order is placed for 400, the rule would alert.). In the event that a rule has its logic field blank, the rule should select all securities. Rule logic should always be a string, but could be a null string or just spaces, so replace with something like 1=1 to avoid errors in that situation. Remember that compliance checks are limited to a specific fund at any point in time, never the whole holdings universe of all funds. 
```python
logic = rule.logic.strip()  # should alwayts be STR, comes from the rule itself in the database (not shown here)
if len(logic) == 0:
    logic = '1=1'  # select all securities, always true
elif logic.lower().startswith('where'):
    logic = logic[5:]  # In case user thinks we need the "WHERE" for the where clause (we don't as it's included by code below, having it twice will cause error)
    # Also in the real code, we should implement logic to prohibit SQL keywords or semicolons, the logic should fail testing and not be allowed into a rule, and when a rule is run, if this check fails the applicaiton should raise an error.
fund.id == 12345  # illustrative, would come from a database query in production, representing the fund and rule attachment being checked
if trade:  
    # if we're running in trade mode, there should be a trade associated with the compliance check being performed, which will have a unique ID that we can use to include in the holdings
    trade_id = trade.id
else:
    trade_id = 0  # If we're running portfolio check without a trade, set this to a value not present in the database so no trades will be included
logic_query_sql = f"SELECT * FROM (SELECT * FROM holdings_staging WHERE fund.id == {fund.id} AND trade.id == {trade_id}) holdings INNER JOIN securities on securities.ticker = holdings.ticker INNER JOIN (SELECT ticker, price FROM securities_price WHERE price_date = SELECT MAX(price_date) FROM securities_price) sp ON securities.ticker = sp.ticker INNER JOIN issuers on issuers.issr_id = securities.issr_id WHERE {logic}"
```

*Please note that we'd like to acknowledge the risk of letting a user enter logic that is executed as raw SQL. Given the nature of this system we consider this risk to be minimal, although it's not a best practice to ignore. Please implement basic checks such as not allowing the user to enter a semicolon, not allowing the rule logic string to contain SQL keywords like " drop ", " insert ", " alter ", " update ", " select " or " delete " (case insensitive). For simplicity this check is not shown in the example above.*

Each compliance test will generally have a numerator and a denominator. The numerator involves some attribute (selected automatically by the system based on the denominator, but will generally always be market value of the holding in the fund, or number of shares held), which will be summed up accross all holdings selected, unless it's a "For Each" denominator. The denominator is selected from a pre-set list of available options in the rule setup. We can calculate the denominator at the time the compliance rule is checked or it's otherwise needed, since these values can change frequently. 

After the logic_query_sql above, we would take the data returned and place it in a dataframe, then take the fields based on the denominator selected to calculate the numerator. 

Denominator Options:
* *Total Assets*: The sum of market value of all holdings of the fund, plus cash. Market value of each holding is calculated as the present price * number of shares. Illustrative Query (for a compliance rule check in a trade where we use holdings_staging, for other situations we'd just use holdings): ```SELECT holdings.ticker, sp.price, holdings.shares FROM (SELECT ticker, fund_id, trade_id, shares FROM holdings_staging WHERE fund.id == {fund.id} AND trade.id == {trade_id}) holdings INNER JOIN (SELECT ticker, price FROM securities_price WHERE price_date = SELECT MAX(price_date) FROM securities_price) sp ON holdings.ticker = sp.ticker``` We would calculate product of the price and shares for each ticker, sum all those values, and then add cash from the fund to get total asssets. Associated numerator: sp.price * holdings.shares (multiply for each holding selected by rule, then sum all, numerator will not include cash). 
* *Net Assets*: The sum of market value of all holdings of the fund, plus cash. Market value of each holding is calculated as the present price * number of shares. Alias for "total assets", with the same functionality, retained for compatibility with langauge from other compliance systems. Associated numerator: sp.price * holdings.shares (multiply for each holding selected by rule, then sum all, numerator will not include cash).
* *Total Assets Ex Cash*: The sum of market value of all securities holdings of the fund, without adding cash. Same calculation method as total assets and net assets, we just don't add the cash from the funds table at the end, only the price * shares of each holding. Associated numerator: sp.price * holdings.shares (multiply for each holding selected by rule, then sum all, numerator will not include cash). 
* *Prohibit*: This is a special denominator that treats each security as "1" intended for where we want to prohibit specified securities completley. If a security is present in the selected holdings, the rule will alert, regardles of the size of the position. Associated numerator: 1, note that the logic for this special denominator does not need to actually calculate any values, it simply alerts for any holding returned by the logic query sql. 
* *Shares Outstanding (For Each)*: The total number of shares of a security. Denominators designated as "for each" will have a different calculation methodology, where the compliance engine will calculate the percentage for each holding, rather than for the fund as a whole. Illustrative Query (for a compliance rule check in a trade where we use holdings_staging, for other situations we'd just use holdings): ```SELECT holdings.ticker, s.shares_outstanding FROM (SELECT ticker, fund_id, trade_id FROM holdings_staging WHERE fund.id == {fund.id} AND trade.id == {trade_id}) holdings INNER JOIN securities S on holdings.ticker = S.ticker``` we would take the table returned by this query and for each position, calculate the numerator and divide by shares outstanding for that ticker. A rule using this denominator thus will execute a separate calculation for every individual holding of the fund, hence the "For Each". If any security alerts, then the entire rule will alert (the rule can generate multiple alerts from a single execution). Associated numerator: holdings.shares (we will calculate holdings.shares / s.shares_outstanding and comparing the result against the alert level based on alert if for each holding individually). 

Each rule will also have an alert level and alert if. The alert level will be a float representing the result of the numerator / denominator calculation, and the alert if will specify if it alerts "above" or "below". If a rule has alert_if "above" and alert_level "10.0" then the rule will alert if the calculated percentage is greater than or equal to 10%. If a rule has alert_if "below" and alert_level 25.0" then the rule will alert if it calculates the percentage is less than or equal to 25%. Note that we always use compare with "greater than or equal to" or "less than or equal to" and the rule should always alert if equal. The alert level and alert if can be null if the denominator is "prohibit" as these fields won't be used for prohibit rules. 

### Example compliance rules (expressed as JSON)

*Please note: while we don't know all the attributes that will be present for securities and issuers at the time of this writing, please assume the below examples represent attributes that will be available in production*

#### Rule 1: Max 30% in GICS technology sector issuers
```
{
    "rule_name" : "Max 30% in GICS technology sector issuers",
    "alert_message" : "This fund can only hold up to 30% in technology sector as defined by GICS",
    "trade_compliance_mode" : True,
    "portfolio_compliance_mode" : False,
    "logic" : "issuers.gics_sector == 'Information Technology'",
    "denominator" : "total_assets",
    "alert_if" : "above",
    "alert_level" : 30.0
}
```
**How we'd process this compliance rule:**
* If the user runs portfolio compliance for an attached fund, this rule would be ignored, as portfolio_compliance_mode is False. 
* If the user places a BUY or SELL order in an attached fund, this rule will be checked as trade_compliance_mode is True
* When this rule is triggered, the first step is to take the universe of holdings of this fund plus the traded security, and compare that with the SQL logic.
* This SQL logic will select all holdings where the issuer's gics_sector is Information Technology
* Once we have the list of selected holdings, we then take the security for each holding and calculate the present market value (the current stock price * number of shares held). Note that the number of shares held would add (or remove) the shares in the trade. 
* We sum up all of the present market value for all selected holdings to get our numerator, the total market value of all securities where the issuer has a gics sector in Information Technology
* For the denominator, we take the sum of the present market value of all holdings of the fund as the rule specifies "Total Assets"
* The numerator / denominator gives us our compliance percentage. If the compliance percentage is "above" (equal to or greater than) the alert level of 30%, we will raise an alert
* The alert should stop the trade, and require action from the user to address (either cancel the trade, or enter an override note and override the alert, allowing them to proceed with the trade but recording their reasoning)

#### Rule 2: Max 10% TA in non Benchmark Constituents (S&P 500)
```
{
    "rule_name" : "Max 10% TA in non Benchmark Constituents (S&P 500)",
    "alert_message" : "This fund is intended to have the S&P 500 as a benchmark, but cannot hold more than 10% of total assets in other securities (ex cash)",
    "trade_compliance_mode" : True,
    "portfolio_compliance_mode" : True,
    "logic" : "holdings.ticker NOT IN ('NVDA', 'MSFT', 'AAPL', 'GOOG', 'GOOGL', 'AMZN', 'V', 'JPM', 'ORCL', 'WMT', 'NFLX', 'JNJ', 'ABBV', 'COST', 'BRK.B', 'TSLA', 'CAT', 'KO', 'WFC', 'MS', 'IBM', 'GE', 'PG', 'TMUS', 'ABT')",
    "denominator" : "total_assets",
    "alert_if" : above,
    "alert_level" : 10
}
```
*Note: S&P 500 security list is illustrative for the purposes of explaining logic function only, in reality there would be many more tickers present*
**How we'd process this compliance rule:**
* If the user runs portfolio compliance for an attached fund, this rule would be checked, as portfolio_compliance_mode is True. 
* If the user places a BUY or SELL order in an attached fund, this rule will be checked as trade_compliance_mode is True
* When this rule is triggered, the first step is to take the universe of holdings of this fund plus the traded security, and compare that with the SQL logic.
* This SQL logic will select all holdings where the ticker is not in the specified list (illustrative above, but this list in reality would have all S&P 500 tickers)
* Once we have the list of selected holdings, we then take the security for each holding and calculate the present market value (the current stock price * number of shares held). Note that the number of shares held would add (or remove) the shares in the trade. 
* We sum up all of the present market value for all selected holdings to get our numerator, the total market value of all securities where the ticker is not in the list.
* For the denominator, we take the sum of the present market value of all holdings of the fund as the rule specifies "Total Assets"
* The numerator / denominator gives us our compliance percentage. If the compliance percentage is "above" (equal to or greater than) the alert level of 10%, we will raise an alert
* The alert should stop the trade, and require action from the user to address (either cancel the trade, or enter an override note and override the alert, allowing them to proceed with the trade but recording their reasoning)

#### Rule 3: No investment in OFAC restricted countries
```
{
    "rule_name" : "No investment in OFAC restricted countries",
    "alert_message" : "US Regulations prohibit transacting in securities based in OFAC restricted countries.",
    "trade_compliance_mode" : True,
    "portfolio_compliance_mode" : True,
    "logic" : "issuer.country_incorporation IN ('PRK', 'MMR', 'TKM')",
    "denominator" : "Prohibit",
    "alert_if" : null,
    "alert_level" : null
}
```
*Note: Country list is illustrative for the purposes of explaining logic function only, not an actual OFAC list*
**How we'd process this compliance rule:**
* If the user runs portfolio compliance for an attached fund, this rule would be checked, as portfolio_compliance_mode is True. 
* If the user places a BUY or SELL order in an attached fund, this rule will be checked as trade_compliance_mode is True
* When this rule is triggered, the first step is to take the universe of holdings of this fund plus the traded security, and compare that with the SQL logic.
* This SQL logic will select all holdings where the issuer's country is included in the specified list, including any applicable holding that would be added if we're checking compliance on a BUY order. 
* The Prohibit denominator triggers special logic, rather than calculating a percentage as most rules do, we alert if any holding is found, regardless of the number of shares or market value.
* If triggered by a BUY or SELL, the alert should stop the trade, and require action from the user to address (either cancel the trade, or enter an override note and override the alert, allowing them to proceed with the trade but recording their reasoning). 

#### Rule 4: Max 5% of shares outstanding in any security 5(b)(1)
```
{
    "rule_name" : "Max 5% of shares outstanding in any security 5(b)(1)",
    "alert_message" : "A US 40 Act fund diversification requirements limits investments in any one issuer to 5% of TNA, for at least 75% of the fund. For safety, we limit shares outstanding to 5% generally.",
    "trade_compliance_mode" : True,
    "portfolio_compliance_mode" : True,
    "logic" : "",
    "denominator" : "shares_outstanding_fe",
    "alert_if" : "above",
    "alert_level" : 5.0
}
```
*Why is the logic blank? This rule we want to check **every** security, blank logic means "all" in this compliance engine. A user could also enter placeholder logic that is always true, like "1=1", or leave blank and the system will do it for them.*
**How we'd process this compliance rule:**
* If the user runs portfolio compliance for an attached fund, this rule would be checked, as portfolio_compliance_mode is True. 
* If the user places a BUY or SELL order in an attached fund, this rule will be checked as trade_compliance_mode is True
* When this rule is triggered, the first step is to take the universe of holdings of this fund plus the traded security, and compare that with the SQL logic.
* This SQL logic will select all securities, excluding cash
* This rule uses a For Each denominator, which means we perform the numerator / denominator calculation for each security in the holdings (incl trade if applicable), rather than on the portfolio as a while. If any of the holdings generate an alert, then this rule generates an alert. 
* For each holding selected, because of this denominator choice, we take the shares held by the fund (+ or - the trade, if applicable) and compare to the holding.shares_outstanding attribute from that security. If any security is found to have greater than or equal to 5% of its shares outstanding held by the fund, then we need to raise an alert. 
* The alert should stop the trade, and require action from the user to address (either cancel the trade, or enter an override note and override the alert, allowing them to proceed with the trade but recording their reasoning). We should make it clear to the user which security triggered the alert. 


# Data Concepts

The system will need to be aware of and work with several key data concepts that should function as objects withtin the software. We will not connect to any external API. 

* Rules for compliance: a rule that checks compliance and contains the logic that is run against each trade. It will have a rune name, alert note, modes for trade and portfolio compliance, alert thresholds, and of course the core logic in the form of SQL.
* Security: an asset that the fund may own (for the purposes of this application, we will just consider equity stocks). Note that this is security in the financial instrument sense, not the safety sense. Note that the concept of a security is an asset that exists in the market which can be bought or sold by funds. Each security will have a name, ticker, and issuer, some number of other attributes, and a price that can change day-to-day. Securities are interchangable, one "share" is the same as any other share. Please ensure the design accounts for any number of securty attributes, as we don't know all the ones we'll include at this time. For ease of use, let's use ticker as the primary key (I recognize this isn't an ideal design, but for simplicity sake it meets the needs of this application). 
* Security Price: a table of prices for each security in cash. Each row in this table will have a security identified by its ticker, a date, and a price (a decimal cash number up to three decimal places). For the purposes of this dataset, we will only take one price per day. 
* Issuer: a company that issues a security. Issuers can issue multiple securities (think multiple share classes of stock, subsidiaries, etc.). Will have a name and some attributes on which compliance may be tested. Please ensure the design accounts for an unknown number of attributes. 
* Fund: a portfolio that holds some number of securities and cash. Funds will generally have a name and a portfolio of some number of holdings.
* Cash: the only thing a fund can hold that isn't a security. You may assume it's US Dollar. We will store in the funds table as each fund will have just one cash value at any time.
* Holding: a security held by a fund. Links Fund to Securities. Each holding will have some market value and number of shares (market value = shares held * current price). Note that any trade will add to or remove from existing holdings, if present (if the fund holds 300 shares of GOOG and buys 200 more, the holding will now be 500 shares, we will not have two separate holding records). 
* Trade: Funds buy and sell securities. A trade will occur at a point in time, it will have an associated fund and security, a direction (BUY or SELL), and an amount of shares (amount of shares * price per share = total value of the trade). Each trade will also have a "status" field tracking how the trade is moving through the trade flow, which will contain one of 'submitted', 'validating', 'invalid', 'compliance', 'alert', 'cancelled', 'processed'
* Holding Staging: a special table that stores holdings modified by trades temporarily while the trade is in process and compliance is being checked. 
* Alert: when a rule is violated, it should create an alert record which links to the rule, the fund, and the trade. The user has the option to cancel the trade, or override the alert, with an optional reason field. Every trade and alert should be logged in a table, except test trades. Alerts can also be triggered on the batch portfolio compliance process, which will also be stored in this table with a field to designate how the alert was triggered. 

## Expected Database Tables to Create and Relationships
* Funds: one record for each fund. Stores all basic data about the fund like fund name, cash, etc.
* Holdings: one fund to many holdings, many holdings to many securities, each holding will have an amount.
* Holdings_Staging: When a trade is placed, we copy the funds holdings into this table and execute the trade against it (add new holding or increase shares for a BUY, and remove security or decrease shares for a SELL). We run compliance against the holdings in this table, and if the compliance check clears or user overrides any alerts, we write the update to the real holdings (and drop the records from this table). Intended as a temporary table to be used in compliance checking process only. 
* Securities: many to many relationship with holdings, one issuer for each security
* Securities_Price: many to one relationship with securities, where each row represents a price at a point in time. 
* Issuers: one issuer to many securities
* Attributes: one issuer or security to many attributes. Each row contains one datum related to one security or issuer. 
* Trades: to store each trade created. Each trade will have one security, one fund. 
* Rules: one row per rule
* Rules_Attachments: many to many relationship between rules and funds (linking table)
* Alerts: each alert should relate to a trade or holding, a fund, and a rule

All tables, incluidng linking tables for many to many relationships (not explicitly listed above but still expected) should follow the best practice of including an integer primary key, except securities which will use ticker. We should also include datetime stamps where appropriate (trade, alert, create and latest update for rules, funds).  

For fields containing timestamps, we will use US Eastern time. 

We intend to have a number of attributes for each security and issuer, but the total list is not known at this time. We'd like to start by developing the base application and enhancing it to add more attributes later. 

Examples of attributes (unless otherwise sepcified, all are nullable). Note that this is not a comprehensive list of columns.
* **securities.shares_outstanding** INT The number of shares of a given security that exist in the investible universe. 
* **securities.market_cap** INT The shares_outstanding times the current price, represents the total value of the company for that security (note: will be big integer not float, we don't need to calculate this but if it ever were we'd just truncate the decimals)
* **securities.type** STR Generally will be "Equity Stock" as we won't consider fixed income / bonds or derivatives for the purposes of this simple app development.
* **securities.name** STR The name of a security. Will include share class information if relevant. 
* **securities.ticker** STR string representing the ticker for a security. We can use as a primary key, for simplicity, for securities
* **issuer.name** STR The name of a company issuing a security. In many cases, for Equity Stock, may end up being the same as securities.name.
* **issuer.gics_sector** STR 
* **issuer.gics_industry_grp** STR
* **issuer.gics_industry** STR
* **issuer.gics_sub_industry** STR
* **issuer.country_domicile** STR
* **issuer.country_incorporation** STR
* **issuer.country_domicile_code** STR three letter code for country, like "USA" 
* **issuer.country_incorporation_code** STR three letter code for country, like "USA" 


# Front End

We want to focus on a simple, easy to use front-end that integrates well with Flask, minimizes complexity and overhead, and can handle the functionality of this application. We recommend the use of Streamlit for this purpose at this stage of the application's lifecycle. 

In general, the API endpoints should provide all the attributes needed by the front end, as the number of discrete application functions is not too excessive. 

A few clarifying points to help with development:
* The application will use one timzeone, US Eastern. The front end can have the option to change time zone (not required at this time but may potentially be needed in future). 
* For the alert review screen, a simple filterable streamlit table is sufficient to review historical alerts. For the user to enter new overrides, we need to ensure we can accept the override reason and let the user choose to override alerts. 
* The compliance check, when triggered, is meant to be an asynchronous process. The GUI can show as a loading screen, but we don't know the amount of time the system will need to execute the check. 
* In general, we should go for a dark theme in streamlit. Default fonts are OK. Please minimize the use of icons / emoji and keep the application's design language professional. 


# User Stories

Please note that we will just have one user role that is able to do everything, through several screens of the application. 

All stories are: "As a user..."

## Trade stories
* I am able to access a fund overview screen that gives a list of all funds, with fund name, cash, and the total number of holdings (count of unique securities) for each. There should be one element per fund, and clicking on any fund takes me to the fund holdings screen. 
* I am able to edit a fund's cash by clicking on an "edit cash" button in the fund overview screen. *Note: in a production ennvironment users would not edit cash, but as this is an educational / testing system and our funds will not have actual investment inflows or outflows, the ability to edit cash is necessary to be able to perform trade activity.*
* I am able to access a fund holdings screen that gives an overview of the fund and its holdings
* On the fund holdings screen I'm able to book a BUY or SELL transaction with a button next to each security (except type == 'cash'). I am able to define how many shares to sell up to the amount held. I am unable to sell securities that the fund does not hold. 
* I have the ability to book a BUY transaction on the fund holdings screen (separate and additional to the BUY button on each holding). I can easily look up securities, enter the amount to buy, and place the order. The system should check that there is sufficient cash in the account. A BUY order may add to an existing holding, or add a new security to the fund. Note that, for the purposes of this system, it is not possible to buy cash (we will not have forex). 
* When placing a BUY order for a security the fund does not hold, I can easily search the universe of investible securities. I can look up securities by ticker, or search based on issuer name using simple "contains" case insensitive search. This means if I search for "disney" I should find the security DIS "The Walt Disney Company" (assuming it's in the database).
* When I place an order for either a BUY or SELL trade, the system should run all compliance rules that are marked for trade compliance and attached to the fund. 
* If any rule exceeds its alert threshold for that fund, the system should give me a pop-up with option to cancel the trade, or override. There should be an optional string field where I can enter an override reason. The pop-up should clearly inform me of the calcluated percentage and the holding(s) that triggered the alert. 
* All alerts should be stored and viewable in an alert review screen, including ones where I've cancelled the order. I should be able to see the associated trade and fund details, the rule name and alert note, the calcluated percentage from the rule, the action taken, and the override reason if applicable. A simple table view will do. 
* I am able to view a table of all securities showing their name, issuer, and current price. I can click on any security to see a detailed view of all attributes

## Compliance Stories
* I am able to access a screen showing all compliance rules in the system
* I am able to filter rules by fund attachment, rule name
* I am able to excecute a search for rules by rule name (simple "contains" search, case insensitive)
* I am able to click a "new rule" button in the bottom right with a plus icon to create a new rule
* I am able to select an existing rule to edit
* On the rule creation / edit screen, I am able to enter all the key details about the rule. 
* I am able to enter the rule logic as a SQL WHERE filter, and the application has the ability to verify the SQL logic is valid. I will get back a clear error message if the SQL fails basic validation checks (semicolons and SQL keywords not allowed), and the API / GUI will pass through any error message if the database cannot successfully execute the query. 
* I am able to select if the rule runs in trade compliance (BOOL) and if it runs in portfolio compliance (BOOL). 
* I am able to link the rule to one or more funds
* I am able to view existing fund links and remove / add more
* I am able to test a rule by selecting a fund and running against its existing holdings (without actually attaching)
* I am able to test a rule by selecting a fund and placing a test BUY or test SELL order (without actually attaching and without actually placing a real order, just checking what the result would be...these orders are not logged)
* I am able to trigger a batch compliance check with a button on the fund overview screen, which will check each rule attached to the fund where the portfolio compliance mode is True, against the holdings of that fund. I am able to view a screen showing all alerts from this process (only the most recent run, although all alerts are stored in the alert table).

## AI Stories

As an AI Agent user...
* I am able to view funds as an MCP resource
* I am able to view holdings for each fund as an MCP Resource
* I am able to view details about any security as an MCP resource (security information and attributes). 
* I am able to view compliance rules and search by fund attachment or rule name as an MCP resource
* I am able to create new compliance rules as an MCP tool providing all required inputs and recieving a response on success or a message as to the reason for failure (improper format, rule name already exists, etc.), including all relevant fields a compliance rule would have. I expect to recieve a message if the SQL provided for rule logic is invalid.
* I am able to place test BUY or SELL orders for a security on a fund using an MCP tool to test compliance rules, these will function just like test orders placed by the user, and I am able to recieve a response that explains the result to me. Example "Test of rule 15512 'Max 12% in issuers in any one country' rule ALERT on test BUY of 10000 shares XYX with concentration of 15.7%"
* I am able to activate or deactivate compliance rules as an MCP tool
* I am able to update existing compliance rules as an MCP tool by informing the system what rule to change, what fields to change, and what values to change. I recieve a response describing the outcome (change is successfully saved, or there's an error like rule doesn't exist, value or field are not valid, etc.)
* I am able to attach or unattach compliance rules to funds as an MCP tool

