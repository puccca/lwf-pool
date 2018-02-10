import requests
import json
import sys
import time

if len (sys.argv) > 2 and sys.argv [1] == '-c':
	cfile = sys.argv [2]
else:
	cfile = 'config.json'
	
try:
	conf = json.load (open (cfile, 'r'))
except:
	print ('Unable to load config file.')
	sys.exit ()
	
if 'logfile' in conf:
	LOGFILE = conf['logfile']
else:
	LOGFILE = 'poollogs.json'


def loadLog ():
	try:
		data = json.load (open (LOGFILE, 'r'))
	except:
		data = {
			"lastpayout": 0, 
			"accounts": {},
			"skip": []
		}
	return data
	
	
def saveLog (log):
	json.dump (log, open (LOGFILE, 'w'), indent=4, separators=(',', ': '))
	


def estimatePayouts (log):
	if conf['coin'].lower () == 'ark':
		uri = conf['node'] + '/api/delegates/forging/getForgedByAccount?generatorPublicKey=' + conf['pubkey']
		d = requests.get (uri)
		lf = log['lastforged']
		rew = int (d.json ()['rewards']) 
		log['lastforged'] = rew 
		rew = rew - lf
	else:
		uri = conf['node'] + '/api/delegates/forging/getForgedByAccount?generatorPublicKey=' + conf['pubkey'] + '&start=' + str (log['lastpayout']) + '&end=' + str (int (time.time ()))
		d = requests.get (uri)
		rew = d.json ()['rewards']

	forged = (int (rew) / 100000000) * conf['percentage'] / 100
	print ('To distribute: %f %s' % (forged, conf['coin']))
	
	if forged < 0.1:
		return ([], log)
		
	d = requests.get (conf['node'] + '/api/delegates/voters?publicKey=' + conf['pubkey']).json ()
	
	weight = 0.0
	payouts = []
	
	for x in d['accounts']:
		if x['balance'] == '0' or x['address'] in conf['skip']:
			continue
			
		weight += float (x['balance']) / 100000000
		
	print ('Total weight is: %f' % weight)
	
	for x in d['accounts']:
		if int (x['balance']) == 0 or x['address'] in conf['skip']:
			continue
			
		payouts.append ({  "username": x['username'], "weight": float (x['balance']) / 100000000, "address": x['address'], "balance": (float (x['balance']) / 100000000 * forged) / weight, "totalweight": weight, "forged": int (rew) / 100000000})
		#print (float (x['balance']) / 100000000, payouts [x['address']], x['address'])
		
	return (payouts, log, forged)
	
	
def pool ():
	log = loadLog ()
	
	(topay, log, forged) = estimatePayouts (log)
	
	if len (topay) == 0:
		print ('Nothing to distribute, exiting...')
		return
		
	f = open ('payments.sh', 'w')
	for x in topay:
		if not (x['address'] in log['accounts']) and x['balance'] != 0.0:
			log['accounts'][x['address']] = { 'username': x['username'], 'weight': x['weight'] / x['totalweight'] * 100, 'pending': 0.0, 'received': 0.0 }
			
		if x['balance'] < conf['minpayout'] and x['balance'] > 0.0:
			log['accounts'][x['address']]['pending'] += x['balance']
			log['accounts'][x['address']]['weight'] = x['weight'] / x['totalweight'] * 100
			continue
			
		log['accounts'][x['address']]['received'] += x['balance'] - conf['fee']
		log['accounts'][x['address']]['weight'] = x['weight'] / x['totalweight'] * 100
		log['totalweight'] = x['totalweight']
		log['forged'] = x['forged']
		log['todistribute'] = x['forged'] * conf['percentage'] / 100

		f.write ('echo Sending ' + str (x['balance'] - conf['fee'])  + ' to ' + x['address'] + '\n')
		
		data = { "secret": conf['secret'], "amount": int ((x['balance'] - conf['fee']) * 100000000), "recipientId": x['address'] }
		if conf['secondsecret'] != None:
			data['secondSecret'] = conf['secondsecret']
		
		f.write ('curl -k -H  "Content-Type: application/json" -X PUT -d \'' + json.dumps (data) + '\' ' + conf['nodepay'] + "/api/transactions\n\n")
		f.write ('sleep ' + conf['sleep'] + '\n')
			
	for y in log['accounts']:
		if log['accounts'][y]['pending'] > conf['minpayout']:
			f.write ('echo Sending pending ' + str (log['accounts'][y]['pending'] - conf['fee']) + ' to ' + y + '\n')
			
			
			data = { "secret": conf['secret'], "amount": int ((log['accounts'][y]['pending'] - conf['fee']) * 100000000), "recipientId": y }
			if conf['secondsecret'] != None:
				data['secondSecret'] = conf['secondsecret']
			
			f.write ('curl -k -H  "Content-Type: application/json" -X PUT -d \'' + json.dumps (data) + '\' ' + conf['nodepay'] + "/api/transactions\n\n")
			log['accounts'][y]['received'] += log['accounts'][y]['pending'] - conf['fee']
			log['accounts'][y]['pending'] = 0.0
			f.write ('sleep ' + conf['sleep'] + '\n')
	log['totalpaid']=0
	log['totalpending']=0
	for z in log['accounts']:
		log['totalpaid']+=log['accounts'][z]['received']
		log['totalpending']+=log['accounts'][z]['pending']

	# Donations
	if 'donations' in conf:
		for y in conf['donations']:
			f.write ('echo Sending donation ' + str (conf['donations'][y]) + ' to ' + y + '\n')
				
			data = { "secret": conf['secret'], "amount": int (conf['donations'][y] * 100000000), "recipientId": y }
			if conf['secondsecret'] != None:
				data['secondSecret'] = conf['secondsecret']
			
			f.write ('curl -k -H  "Content-Type: application/json" -X PUT -d \'' + json.dumps (data) + '\' ' + conf['nodepay'] + "/api/transactions\n\n")
			f.write ('sleep ' + conf['sleep'] + '\n')

	# Donation percentage
	if 'donationspercentage' in conf:
		for y in conf['donationspercentage']:
			am = (forged * conf['donationspercentage'][y]) / 100
			
			f.write ('echo Sending donation ' + str (conf['donationspercentage'][y]) + '% \(' + str (am) + 'LSK\) to ' + y + '\n')
				
			data = { "secret": conf['secret'], "amount": int (am * 100000000), "recipientId": y }
			if conf['secondsecret'] != None:
				data['secondSecret'] = conf['secondsecret']
			
			f.write ('curl -k -H  "Content-Type: application/json" -X PUT -d \'' + json.dumps (data) + '\' ' + conf['nodepay'] + "/api/transactions\n\n")
			f.write ('sleep ' + conf['sleep'] + '\n')

	f.close ()
	
	log['lastpayout'] = int (time.time ())
	
	print (json.dumps (log, indent=4, separators=(',', ': ')))
	
	if len (sys.argv) > 1 and sys.argv[1] == '-y':
		print ('Saving...')
		saveLog (log)
	else:
		yes = input ('save? y/n: ')
		if yes == 'y':
			saveLog (log)
			
			

if __name__ == "__main__":
	pool ()
