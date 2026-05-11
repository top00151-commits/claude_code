-- z77 가상 데이터 롤백 SQL
-- 생성: 2026-05-11T23:24:18.948240
-- 모든 z77 더미 식별: note LIKE '%[Z77-DUMMY]%'

BEGIN;
DELETE FROM po_items
 WHERE po_id IN (SELECT id FROM purchase_orders WHERE note LIKE '%[Z77-DUMMY]%');
DELETE FROM purchase_orders WHERE note LIKE '%[Z77-DUMMY]%';
DELETE FROM parts            WHERE note LIKE '%[Z77-DUMMY]%';
DELETE FROM suppliers        WHERE note LIKE '%[Z77-DUMMY]%';
DELETE FROM tickets          WHERE accept_note LIKE '%[Z77-DUMMY]%';
DELETE FROM changes          WHERE description LIKE '%[Z77-DUMMY]%';
DELETE FROM issues           WHERE description LIKE '%[Z77-DUMMY]%';
DELETE FROM board_posts      WHERE body LIKE '%[Z77-DUMMY]%';
COMMIT;
VACUUM;
