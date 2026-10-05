
/* source file (string position, lower evidence than a direct reference):
   ../fr2/source/hscore/hscore.c */

undefined4 FUN_001fb830(undefined8 param_1,undefined8 param_2,int param_3)

{
  undefined4 uVar1;
  uint uVar2;
  int iVar3;
  uint uVar4;
  undefined4 *puVar5;
  
  FUN_0020c7fc(param_2,0);
  uVar4 = (int)param_2 + 3U & 0xfffffffc;
  uVar2 = param_3 - (uVar4 - (int)param_2);
  if (uVar2 < 0x10c0) {
    FUN_001fc4e0(uVar4,0x28b490);
    uVar1 = 0;
  }
  else {
    iVar3 = uVar4 + 0x108;
    puVar5 = (undefined4 *)param_1;
    puVar5[0x10] = uVar4;
    FUN_001fbd88(iVar3,uVar4 + 0x10c0,uVar2 - 0x10c0);
    *puVar5 = 0;
    puVar5[1] = 0;
    puVar5[2] = 0;
    *(undefined8 *)(puVar5 + 4) = 0xffffffffffffffff;
    *(undefined8 *)(puVar5 + 6) = 0xffffffffffffffff;
    *(undefined8 *)(puVar5 + 8) = 0;
    *(undefined8 *)(puVar5 + 10) = 0xffffffffffffffff;
    *(undefined8 *)(puVar5 + 0xc) = 0xffffffffffffffff;
    *(undefined8 *)(puVar5 + 0xe) = 0;
    *(undefined4 *)(uVar4 + 0xb4) = 0;
    *(undefined4 *)(uVar4 + 0xb8) = 0;
    *(undefined4 *)(uVar4 + 0xbc) = 0;
    *(undefined4 *)(uVar4 + 0xc0) = 0;
    *(undefined4 *)(uVar4 + 0xc4) = 0;
    *(undefined4 *)(uVar4 + 200) = 0;
    *(undefined4 *)(uVar4 + 0xcc) = 0;
    *(undefined4 *)(uVar4 + 0xd0) = 0;
    *(undefined4 *)(uVar4 + 0xd4) = 0;
    *(undefined4 *)(uVar4 + 0xd8) = 0;
    *(undefined4 *)(uVar4 + 0xdc) = 0;
    *(undefined4 *)(uVar4 + 0xe0) = 0;
    *(undefined4 *)(uVar4 + 0xe4) = 0;
    *(undefined4 *)(uVar4 + 0xe8) = 0;
    *(undefined4 *)(uVar4 + 0xf8) = 0;
    *(undefined4 *)(uVar4 + 0xc) = 0;
    *(undefined4 *)(uVar4 + 0x14) = 0;
    *(undefined4 *)(uVar4 + 0x2c) = 0;
    *(undefined4 *)(uVar4 + 0x34) = 0;
    *(undefined4 *)(uVar4 + 0x3c) = 0;
    *(undefined8 *)(uVar4 + 0xf0) = 0xffffffffffffffff;
    *(code **)(uVar4 + 0x1c) = candidate_ee_001fcde8;
    *(code **)(uVar4 + 0x24) = candidate_ee_001fcdf8;
    uVar1 = FUN_001fbdc0(uVar4,iVar3,0x600,8);
    *(undefined4 *)(uVar4 + 0x48) = 0;
    *(undefined4 *)(uVar4 + 0xfc) = 0;
    *(undefined4 *)(uVar4 + 0x100) = 0;
    *(undefined4 *)(uVar4 + 0x104) = 0;
    *(undefined4 *)(uVar4 + 0x70) = 0;
    *(undefined8 *)(uVar4 + 0x78) = 0;
    *(undefined4 *)(uVar4 + 0x80) = 0xffffffff;
    *(undefined8 *)(uVar4 + 0x88) = 0;
    *(undefined4 *)(uVar4 + 0x90) = 0;
    *(undefined4 *)(uVar4 + 0xac) = 0;
    *(undefined4 *)(uVar4 + 0x94) = 0xffffffff;
    *(undefined4 *)(uVar4 + 0x98) = 0xffffffff;
    *(undefined4 *)(uVar4 + 0x9c) = 0xffffffff;
    *(undefined4 **)(uVar4 + 0x858) = puVar5;
    *(undefined4 *)(uVar4 + 0x44) = uVar1;
    *(undefined4 *)(uVar4 + 0xb0) = 1;
    FUN_001fc370(uVar4);
    FUN_001fbba0(param_1);
    FUN_001fbbf0(param_1);
    *(uint *)(uVar4 + 0x1b8) = uVar4 + 0x1e8;
    *(uint *)(uVar4 + 0x1bc) = uVar4 + 0x250;
    *(uint *)(uVar4 + 0x1c4) = uVar4 + 0x2b8;
    *(uint *)(uVar4 + 0x1c8) = uVar4 + 800;
    *(uint *)(uVar4 + 0x1cc) = uVar4 + 0x388;
    *(uint *)(uVar4 + 0x1d4) = uVar4 + 0x3f0;
    *(uint *)(uVar4 + 0x1d8) = uVar4 + 0x458;
    *(uint *)(uVar4 + 0x1dc) = uVar4 + 0x4c0;
    *(uint *)(uVar4 + 0x1e4) = uVar4 + 0x528;
    FUN_001fbda0(iVar3);
    *(undefined4 *)(uVar4 + 0x850) = 0xffffffff;
    uVar1 = 0x70003600;
    *(undefined4 *)(uVar4 + 0x854) = 0;
    *(undefined4 *)(uVar4 + 0x81c) = 0x70003600;
    *(undefined4 *)(uVar4 + 0x84c) = 0;
  }
  return uVar1;
}

