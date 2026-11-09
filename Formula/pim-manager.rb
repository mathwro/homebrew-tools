class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.1/pim-manager_0.4.1_darwin_arm64.tar.gz"
      sha256 "623def842c095c8499cb20c5e6085f763babcc47324df71add4833de1157cafa"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.1/pim-manager_0.4.1_darwin_amd64.tar.gz"
      sha256 "53b54c61418f1a0b7eafad3b72fe197920b37792b2fe39f234e3c5978438a0ee"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.1/pim-manager_0.4.1_linux_arm64.tar.gz"
      sha256 "07e9f83fd78d8684553584ba4dee40ec9edfef7a4dd56d0db6850072895f0d85"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.1/pim-manager_0.4.1_linux_amd64.tar.gz"
      sha256 "be1b41cbf6f2a1ee6fb245674896ed513de97c473615ad16908f94db4bc55433"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
