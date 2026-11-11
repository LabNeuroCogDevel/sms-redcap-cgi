<?php
/*
  twilio hook to forward all SMS text messages to email
 20261027WF - init
*/

// where to forward emails
$FWD_EMAIL="lncd@pitt.edu";

// mail all of _POST with 
function send_mailnotify() {
    global $FWD_EMAIL;
    $to = $FWD_EMAIL;
    $from = $FWD_EMAIL;
    # [+11234567890] Blah blah blah
    $subject = "[" . ($_POST['From'] ?? '(No number!)') ."] " . ($_POST['Body'] ?? '(no message)')  ;
    // list out all the parameters that were submitted
    $message = urldecode(http_build_query($_POST,"\n","\n"));
    # could send all the server header information we have (done for email, not for this web hook)
    #$message .= "\n------\n" . urldecode(http_build_query(apache_request_headers(),"\n","\n"));

    $headers = "From:" . $from;
    if(getenv("DRYRUN")){
        echo "# mail to '$to' from '$from' subj '$subject'\n'$message'";
    } else {
       mail($to,$subject,$message,$headers);
    }
}

// Not POST? Not from Twilio or something else is wrong
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo "Expected POST request\n";
    exit("Rejected");
}
// dumb check to avoid spam. could validate data w/signature
// $_SERVER['HTTP_X_TWILIO_SIGNATURE'] hash with TWILIO_AUTH_TOKEN
// https://....php?hook_key=secret
$keycheck = hash_hmac('sha256', ($_GET['hook_key'] ??''), '');
$secret_hash = 'a956cb73bece27af32234cc4bdc8467a54a4f77fb7a74bd59d7e388b7a02cb5c';
if($keycheck != $secret_hash){
    http_response_code(405);
    echo "Missing auth code\n";
    exit("Rejected");
}

// Only process authenticated requests from here on.
if (($_POST['From'] ?? '')  === '' || ($_POST['MessageSid'] ?? '') === '') {
    http_response_code(400);
    echo "Missing information\n";
    exit("Rejected");
}

// tell twilio not send an automatic SMS reply.
header('Content-Type: text/xml; charset=utf-8');
send_mailnotify();
echo '<?xml version="1.0" encoding="UTF-8"?>'
   . '<Response></Response>';

