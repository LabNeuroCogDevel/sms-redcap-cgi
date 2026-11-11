<?php
putenv('DRYRUN=1');
$_SERVER['REQUEST_METHOD'] = 'POST';
$env = parse_ini_file('.twilio_env');
$_GET['hook_key'] = $env['GETKEYSECRET'];
#$_GET['hook_key'] .= 'wrong';
$_POST = [
    'From' => '+15551234567',
    'To' => '+15557654321',
    'Body' => 'Test message',
    'MessageSid' => 'TEST123',
];

require 'email-fwd.php';
