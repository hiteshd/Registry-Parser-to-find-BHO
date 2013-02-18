TRUNCATE TABLE executions cascade;

TRUNCATE TABLE chrome cascade;

TRUNCATE TABLE msie cascade;

TRUNCATE TABLE mappings cascade;

insert into chrome(id,registry_key,bho_name) values('0','FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF','REFER_FIREFOX_OR_MSIE');

insert into msie(id,registry_key,bho_name) values('0','FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF','REFER_FIREFOX_OR_CHROME');
