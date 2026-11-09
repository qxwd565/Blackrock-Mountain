<?php
/** Offline check of UNMODIFIED plugin sources. No WordPress or network writes. */
define('ABSPATH', __DIR__); define('HSCARD_VERSION','offline-test');
error_reporting(E_ALL);
set_error_handler(function($level,$message,$file,$line){if(error_reporting() & $level){throw new ErrorException($message,0,$level,$file,$line);}return false;});
class WP_Error { public $message; function __construct($code,$message=''){ $this->message=$message; } }
function __($text,$domain=''){return $text;}
function absint($value){return abs((int)$value);}
function sanitize_text_field($value){return strip_tags((string)$value);}
function esc_url_raw($value){return (string)$value;}
function wp_parse_url($value,$component=-1){return parse_url($value,$component);}
function is_wp_error($value){return $value instanceof WP_Error;}
$base=$argv[1];$fixture=json_decode(file_get_contents($argv[2]),true);
require $base.'/includes/class-set-api.php';require $base.'/includes/class-card-history.php';
$api=new HScard\Set_API();
$parsed=$api->parse_json(json_encode($fixture['catalog']),'https://raw.githubusercontent.com/qxwd565/Blackrock-Mountain/main/cards.json');
if(is_wp_error($parsed)){throw new Exception($parsed->message);}
if(count($parsed['cards'])!==$fixture['expectedCards']){throw new Exception('Import removed cards');}
$original=$api->parse_json(json_encode($fixture['originalCatalog']),$fixture['baseUrl'].'cards.json');
if(is_wp_error($original)||$original!==$parsed){throw new Exception('Current imported values changed');}
$input=array();foreach($fixture['catalog']['cards'] as $row){$input[$row['dbfId']]=$row;}
foreach($parsed['cards'] as $row){
 $expected=$input[$row['id']];
 if($row['card_code']!==$expected['id']||$row['mana']!==$expected['cost']||$row['card_type']!==$expected['type']){throw new Exception('Imported identity/stat mismatch');}
 foreach(array('attack','health','durability','armor') as $field){if($row[$field]!==$expected[$field]){throw new Exception('Imported numeric mismatch');}}
 if($row['art']!==$fixture['baseUrl'].$expected['art']){throw new Exception('Imported art base changed');}
}
$current=array();foreach($fixture['catalog']['cards'] as $card){$current[$card['dbfId']]=$card;}
$checks=1;
foreach($fixture['cases'] as $case){
 $id=$case['dbfId'];$history=isset($fixture['history']['cards'][(string)$id])?$fixture['history']['cards'][(string)$id]['history']:array();
 $actual=array_replace($current[$id],HScard\Card_History::resolve($history,$case['date']));
 $actual=array_intersect_key($actual,array_flip($fixture['allowed']));
 $expected=$case['expected'];ksort($actual);ksort($expected);
 if($actual!==$expected){throw new Exception($case['id'].' '.$case['date'].' old parser mismatch');}
 ++$checks;
}
echo json_encode(array('php'=>PHP_VERSION,'plugin'=>'unmodified pinned base','importedCards'=>count($parsed['cards']),'checks'=>$checks,'passed'=>true))."\n";
