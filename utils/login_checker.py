def check_login(request, logger):
    x_forwarded_for = request.META.get('HTTP_X_REAL_IP')
    ip = ""
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    
    logger.info('ip : %s %s'%(ip,ip.split('.')[0]))
    logger.info('user.is_authenticated : %s'%(request.user.is_authenticated))
    logger.info((ip != "" and int(ip.split('.')[0]) != 192))
    if (not request.user.is_authenticated) and (ip != "" and int(ip.split('.')[0]) != 192):
        return True
    else:
        return False

