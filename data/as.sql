BEGIN TRANSACTION;
DROP TABLE IF EXISTS "AuthAudit";
CREATE TABLE "AuthAudit" (
	"AuditId"	INTEGER,
	"Username"	TEXT,
	"Success"	INTEGER NOT NULL,
	"Reason"	TEXT,
	"CreatedAt"	TEXT NOT NULL,
	PRIMARY KEY("AuditId" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "Permissions";
CREATE TABLE "Permissions" (
	"PermissionId"	INTEGER,
	"PermissionKey"	TEXT NOT NULL UNIQUE,
	"Description"	TEXT,
	PRIMARY KEY("PermissionId" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "RolePermissions";
CREATE TABLE "RolePermissions" (
	"RoleId"	INTEGER NOT NULL,
	"PermissionId"	INTEGER NOT NULL,
	PRIMARY KEY("RoleId","PermissionId")
);
DROP TABLE IF EXISTS "Roles";
CREATE TABLE "Roles" (
	"RoleId"	INTEGER,
	"RoleName"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("RoleId" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "UserRoles";
CREATE TABLE "UserRoles" (
	"UserId"	INTEGER NOT NULL,
	"RoleId"	INTEGER NOT NULL,
	PRIMARY KEY("UserId","RoleId")
);
DROP TABLE IF EXISTS "Users";
CREATE TABLE "Users" (
	"UserId"	INTEGER,
	"Username"	TEXT NOT NULL UNIQUE,
	"PasswordHash"	TEXT NOT NULL,
	"IsActive"	INTEGER NOT NULL DEFAULT 1,
	"CreatedAt"	TEXT NOT NULL,
	"LastLoginAt"	TEXT,
	"MustChangePassword"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("UserId" AUTOINCREMENT)
);
INSERT INTO "AuthAudit" VALUES (1,'admin',1,'ok','2026-02-27T13:07:39.879326');
INSERT INTO "AuthAudit" VALUES (2,'deneme',1,'ok','2026-02-27T13:08:30.524416');
INSERT INTO "AuthAudit" VALUES (3,'admin',1,'ok','2026-02-27T13:13:21.211811');
INSERT INTO "AuthAudit" VALUES (4,'admin',1,'ok','2026-02-27T13:17:46.530049');
INSERT INTO "AuthAudit" VALUES (5,'admin',1,'ok','2026-02-27T13:31:37.289848');
INSERT INTO "AuthAudit" VALUES (6,'admin',1,'ok','2026-02-27T13:34:27.796971');
INSERT INTO "AuthAudit" VALUES (7,'admin',1,'ok','2026-02-27T13:40:20.097898');
INSERT INTO "AuthAudit" VALUES (8,'admin',1,'ok','2026-02-27T14:00:34.192734');
INSERT INTO "AuthAudit" VALUES (9,'admin',1,'ok','2026-02-27T14:03:16.041092');
INSERT INTO "AuthAudit" VALUES (10,'admin',1,'ok','2026-02-27T14:47:09.957273');
INSERT INTO "AuthAudit" VALUES (11,'admin',1,'ok','2026-03-02T08:33:11.317099');
INSERT INTO "AuthAudit" VALUES (12,'admin',1,'ok','2026-03-02T08:43:49.369785');
INSERT INTO "AuthAudit" VALUES (13,'admin',1,'ok','2026-03-02T08:50:09.365533');
INSERT INTO "AuthAudit" VALUES (14,'admin',1,'ok','2026-03-02T08:53:01.525667');
INSERT INTO "AuthAudit" VALUES (15,'admin',1,'ok','2026-03-02T08:56:05.650839');
INSERT INTO "AuthAudit" VALUES (16,'admin',1,'ok','2026-03-02T08:57:54.332097');
INSERT INTO "AuthAudit" VALUES (17,'admin',1,'ok','2026-03-02T09:04:40.299930');
INSERT INTO "AuthAudit" VALUES (18,'admin',1,'ok','2026-03-02T09:11:44.398253');
INSERT INTO "AuthAudit" VALUES (19,'admin',1,'ok','2026-03-02T09:15:24.674973');
INSERT INTO "AuthAudit" VALUES (20,'admin',1,'ok','2026-03-02T09:16:54.946472');
INSERT INTO "AuthAudit" VALUES (21,'admin',1,'ok','2026-03-02T09:21:07.209066');
INSERT INTO "AuthAudit" VALUES (22,'admin',1,'ok','2026-03-02T09:35:10.292297');
INSERT INTO "AuthAudit" VALUES (23,'admin',1,'ok','2026-03-02T09:51:25.091182');
INSERT INTO "AuthAudit" VALUES (24,'admin',1,'ok','2026-03-02T10:06:32.020957');
INSERT INTO "AuthAudit" VALUES (25,'admin',1,'ok','2026-03-02T10:11:11.285666');
INSERT INTO "AuthAudit" VALUES (26,'admin',1,'ok','2026-03-02T10:12:50.817320');
INSERT INTO "AuthAudit" VALUES (27,'admin',1,'ok','2026-03-02T10:14:02.624179');
INSERT INTO "AuthAudit" VALUES (28,'admin',1,'ok','2026-03-02T10:17:46.837815');
INSERT INTO "AuthAudit" VALUES (29,'admin',1,'ok','2026-03-02T10:50:52.114295');
INSERT INTO "AuthAudit" VALUES (30,'admin',1,'ok','2026-03-02T10:52:03.252254');
INSERT INTO "AuthAudit" VALUES (31,'admin',1,'ok','2026-03-02T10:57:35.055820');
INSERT INTO "AuthAudit" VALUES (32,'admin',1,'ok','2026-03-02T11:00:22.033273');
INSERT INTO "AuthAudit" VALUES (33,'admin',1,'ok','2026-03-02T11:05:49.088111');
INSERT INTO "AuthAudit" VALUES (34,'admin',1,'ok','2026-03-02T11:07:29.046162');
INSERT INTO "AuthAudit" VALUES (35,'admin',1,'ok','2026-03-02T11:09:27.630088');
INSERT INTO "AuthAudit" VALUES (36,'admin',1,'ok','2026-03-02T11:12:19.147429');
INSERT INTO "AuthAudit" VALUES (37,'admin',1,'ok','2026-03-02T11:15:48.499010');
INSERT INTO "AuthAudit" VALUES (38,'admin',1,'ok','2026-03-02T11:23:45.184154');
INSERT INTO "AuthAudit" VALUES (39,'admin',1,'ok','2026-03-02T11:24:59.242455');
INSERT INTO "AuthAudit" VALUES (40,'admin',1,'ok','2026-03-02T11:31:00.942577');
INSERT INTO "AuthAudit" VALUES (41,'admin',1,'ok','2026-03-02T11:46:23.183710');
INSERT INTO "AuthAudit" VALUES (42,'admin',1,'ok','2026-03-02T11:50:22.066509');
INSERT INTO "AuthAudit" VALUES (43,'admin',1,'ok','2026-03-02T11:54:07.817838');
INSERT INTO "AuthAudit" VALUES (44,'admin',1,'ok','2026-03-02T11:56:20.365369');
INSERT INTO "AuthAudit" VALUES (45,'admin',1,'ok','2026-03-02T11:59:45.129735');
INSERT INTO "AuthAudit" VALUES (46,'admin',1,'ok','2026-03-02T12:03:38.168221');
INSERT INTO "AuthAudit" VALUES (47,'admin',1,'ok','2026-03-02T12:49:48.104983');
INSERT INTO "AuthAudit" VALUES (48,'admin',1,'ok','2026-03-02T12:52:43.194351');
INSERT INTO "AuthAudit" VALUES (49,'admin',1,'ok','2026-03-02T13:05:48.527922');
INSERT INTO "AuthAudit" VALUES (50,'admin',1,'ok','2026-03-02T13:08:14.903167');
INSERT INTO "AuthAudit" VALUES (51,'admin',1,'ok','2026-03-02T13:15:24.056853');
INSERT INTO "AuthAudit" VALUES (52,'admin',1,'ok','2026-03-02T13:16:49.450102');
INSERT INTO "AuthAudit" VALUES (53,'admin',1,'ok','2026-03-02T13:18:21.465869');
INSERT INTO "AuthAudit" VALUES (54,'admin',1,'ok','2026-03-02T13:24:49.266033');
INSERT INTO "AuthAudit" VALUES (55,'admin',1,'ok','2026-03-02T13:30:38.532412');
INSERT INTO "AuthAudit" VALUES (56,'admin',0,'bad_password','2026-03-02T13:31:27.241585');
INSERT INTO "AuthAudit" VALUES (57,'admin',1,'ok','2026-03-02T13:31:32.909694');
INSERT INTO "AuthAudit" VALUES (58,'admin',1,'ok','2026-03-02T13:32:06.832280');
INSERT INTO "AuthAudit" VALUES (59,'admin',1,'ok','2026-03-02T13:46:34.621455');
INSERT INTO "AuthAudit" VALUES (60,'admin',1,'ok','2026-03-02T13:53:19.611396');
INSERT INTO "AuthAudit" VALUES (61,'admin',1,'ok','2026-03-02T14:12:03.429177');
INSERT INTO "AuthAudit" VALUES (62,'admin',1,'ok','2026-03-02T14:17:33.603758');
INSERT INTO "AuthAudit" VALUES (63,'admin',1,'ok','2026-03-02T14:20:30.861048');
INSERT INTO "AuthAudit" VALUES (64,'admin',1,'ok','2026-03-02T14:24:44.821093');
INSERT INTO "AuthAudit" VALUES (65,'admin',1,'ok','2026-03-02T14:33:55.477916');
INSERT INTO "AuthAudit" VALUES (66,'admin',1,'ok','2026-03-02T14:37:43.951992');
INSERT INTO "AuthAudit" VALUES (67,'admin',0,'bad_password','2026-03-02T14:44:49.462992');
INSERT INTO "AuthAudit" VALUES (68,'admin',0,'bad_password','2026-03-02T14:44:56.094350');
INSERT INTO "AuthAudit" VALUES (69,'admin',1,'ok','2026-03-02T14:45:04.957124');
INSERT INTO "AuthAudit" VALUES (70,'admin',1,'ok','2026-03-04T08:30:02.072536');
INSERT INTO "AuthAudit" VALUES (71,'admin',1,'ok','2026-03-04T08:43:41.792102');
INSERT INTO "AuthAudit" VALUES (72,'admin',1,'ok','2026-03-04T08:44:34.668299');
INSERT INTO "AuthAudit" VALUES (73,'admin',1,'ok','2026-03-04T08:49:06.298262');
INSERT INTO "AuthAudit" VALUES (74,'admin',1,'ok','2026-03-04T08:49:56.896098');
INSERT INTO "AuthAudit" VALUES (75,'admin',0,'bad_password','2026-03-04T08:58:37.801296');
INSERT INTO "AuthAudit" VALUES (76,'admin',1,'ok','2026-03-04T08:58:42.644213');
INSERT INTO "AuthAudit" VALUES (77,'admin',1,'ok','2026-03-04T08:59:49.977449');
INSERT INTO "AuthAudit" VALUES (78,'admin',1,'ok','2026-03-04T09:02:28.165834');
INSERT INTO "AuthAudit" VALUES (79,'admin',1,'ok','2026-03-04T09:14:58.760382');
INSERT INTO "AuthAudit" VALUES (80,'admin',1,'ok','2026-03-04T09:16:19.036347');
INSERT INTO "AuthAudit" VALUES (81,'admin',1,'ok','2026-03-04T09:17:16.278676');
INSERT INTO "AuthAudit" VALUES (82,'admin',1,'ok','2026-03-04T09:20:34.363148');
INSERT INTO "AuthAudit" VALUES (83,'admin',1,'ok','2026-03-04T09:21:01.727864');
INSERT INTO "AuthAudit" VALUES (84,'admin',1,'ok','2026-03-04T09:24:05.147566');
INSERT INTO "AuthAudit" VALUES (85,'admin',1,'ok','2026-03-04T09:27:56.730417');
INSERT INTO "AuthAudit" VALUES (86,'admin',1,'ok','2026-03-04T09:31:54.327866');
INSERT INTO "AuthAudit" VALUES (87,'admin',1,'ok','2026-03-04T09:42:09.588822');
INSERT INTO "AuthAudit" VALUES (88,'admin',1,'ok','2026-03-04T09:54:29.996801');
INSERT INTO "AuthAudit" VALUES (89,'admin',1,'ok','2026-03-04T10:01:57.371557');
INSERT INTO "AuthAudit" VALUES (90,'admin',1,'ok','2026-03-04T10:03:31.680659');
INSERT INTO "AuthAudit" VALUES (91,'admin',1,'ok','2026-03-04T10:07:42.435966');
INSERT INTO "AuthAudit" VALUES (92,'admin',1,'ok','2026-03-04T10:33:14.810689');
INSERT INTO "AuthAudit" VALUES (93,'admin',1,'ok','2026-03-04T10:48:43.139838');
INSERT INTO "AuthAudit" VALUES (94,'admin',1,'ok','2026-03-04T10:55:59.072852');
INSERT INTO "AuthAudit" VALUES (95,'admin',1,'ok','2026-03-04T11:14:46.120344');
INSERT INTO "AuthAudit" VALUES (96,'admin',1,'ok','2026-03-04T11:21:04.332707');
INSERT INTO "AuthAudit" VALUES (97,'admin',1,'ok','2026-03-04T11:21:49.835860');
INSERT INTO "AuthAudit" VALUES (98,'admin',1,'ok','2026-03-05T08:58:05.701526');
INSERT INTO "AuthAudit" VALUES (99,'admin',1,'ok','2026-03-05T09:10:01.380688');
INSERT INTO "AuthAudit" VALUES (100,'admin',1,'ok','2026-03-05T10:30:23.420793');
INSERT INTO "AuthAudit" VALUES (101,'admin',1,'ok','2026-03-05T10:32:27.130224');
INSERT INTO "AuthAudit" VALUES (102,'admin',1,'ok','2026-03-05T10:35:08.773100');
INSERT INTO "AuthAudit" VALUES (103,'admin',1,'ok','2026-03-05T10:38:18.513692');
INSERT INTO "AuthAudit" VALUES (104,'admin',1,'ok','2026-03-05T10:49:47.744802');
INSERT INTO "Permissions" VALUES (1,'personel.read','Personel okuma');
INSERT INTO "Permissions" VALUES (2,'personel.write','Personel yazma');
INSERT INTO "Permissions" VALUES (3,'cihaz.read','Cihaz okuma');
INSERT INTO "Permissions" VALUES (4,'cihaz.write','Cihaz yazma');
INSERT INTO "Permissions" VALUES (5,'admin.panel','Admin panel erişimi');
INSERT INTO "Permissions" VALUES (6,'admin.logs.view','Log görüntüleme');
INSERT INTO "Permissions" VALUES (7,'admin.backup','Yedek yönetimi');
INSERT INTO "Permissions" VALUES (8,'admin.settings','Ayarlar yönetimi');
INSERT INTO "Permissions" VALUES (9,'admin.critical','');
INSERT INTO "RolePermissions" VALUES (1,7);
INSERT INTO "RolePermissions" VALUES (1,6);
INSERT INTO "RolePermissions" VALUES (1,5);
INSERT INTO "RolePermissions" VALUES (1,8);
INSERT INTO "RolePermissions" VALUES (1,3);
INSERT INTO "RolePermissions" VALUES (1,4);
INSERT INTO "RolePermissions" VALUES (1,1);
INSERT INTO "RolePermissions" VALUES (1,2);
INSERT INTO "RolePermissions" VALUES (2,1);
INSERT INTO "RolePermissions" VALUES (2,2);
INSERT INTO "RolePermissions" VALUES (2,3);
INSERT INTO "RolePermissions" VALUES (2,4);
INSERT INTO "RolePermissions" VALUES (3,1);
INSERT INTO "RolePermissions" VALUES (3,3);
INSERT INTO "RolePermissions" VALUES (1,9);
INSERT INTO "Roles" VALUES (1,'admin');
INSERT INTO "Roles" VALUES (2,'operator');
INSERT INTO "Roles" VALUES (3,'viewer');
INSERT INTO "UserRoles" VALUES (1,1);
INSERT INTO "UserRoles" VALUES (2,3);
INSERT INTO "UserRoles" VALUES (3,2);
INSERT INTO "Users" VALUES (1,'admin','pbkdf2_sha256$120000$UFZnf2xFvTWDwC02hsiPeA==$p5ciaaiY0medbHSbkGtrweqsYVBQzkMxEBwYVDyGbq4=',1,'',NULL,0);
INSERT INTO "Users" VALUES (2,'viewer','pbkdf2_sha256$120000$Zim3g9q/FkPbuuoVnX/7Ew==$9z94J0nb+l6JBe1cly1HzXGsf90erfcbuKG10e9rtTQ=',1,'2026-02-27T11:59:47.665467',NULL,0);
INSERT INTO "Users" VALUES (3,'deneme','pbkdf2_sha256$120000$XNh0SIpWbtmlUo2FT25JEg==$wYX22LFd96DT3BF6OfqIAHxAMBcQhqp/Gv0TP2617OU=',1,'2026-02-27T13:08:12.347876',NULL,0);
COMMIT;
